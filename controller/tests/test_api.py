from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from axion_controller.main import create_app
from axion_controller.simulator import Simulator


class Clock:
    now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float = 1) -> None:
        self.now += seconds


@pytest.fixture
def controller() -> tuple[TestClient, Clock]:
    clock = Clock()
    return TestClient(create_app(Simulator(initial_pieces=2, clock=clock))), clock


def submit(client: TestClient, command_id: str, kind: str, **parameters: object):
    return client.post(
        "/api/comandos", json={"id": command_id, "tipo": kind, "parametros": parameters}
    )


@pytest.fixture
def run_command(controller: tuple[TestClient, Clock]) -> Callable:
    client, clock = controller

    def run(command_id: str, kind: str, **parameters: object) -> dict:
        response = submit(client, command_id, kind, **parameters)
        assert response.status_code == 202, response.text
        assert response.json() == {"id": command_id, "estado": "aceito"}
        clock.advance(5)
        result = client.get(f"/api/comandos/{command_id}").json()
        assert result["estado"] == "concluido"
        return result

    return run


def test_cubo_do_armazem_ao_estoque_final(controller, run_command):
    client, _ = controller
    run_command("1", "referenciar_mesa")
    run_command("2", "coletar_peca", origem="ARMAZEM_01")
    run_command("3", "mover_para", destino="LEITOR_RFID")
    entry = run_command("4", "ler_rfid", ponto="LEITOR_RFID")
    run_command("5", "depositar_peca", destino="M1")
    run_command("6", "iniciar_processamento", maquina_id="M1", duracao_ms=500)
    run_command("7", "coletar_peca", origem="M1")
    run_command("8", "depositar_peca", destino="QA")
    final = run_command("9", "ler_rfid", ponto="QA")
    assert final["resultado"] == entry["resultado"] == {"rfid": "SIM-001"}
    run_command("10", "coletar_peca", origem="QA")
    run_command("11", "depositar_peca", destino="ESTOQUE_FINAL_01")
    status = client.get("/api/status").json()
    assert {slot for slot, occupied in status["ocupacao"].items() if occupied} == {
        "ARMAZEM_02",
        "ESTOQUE_FINAL_01",
    }
    assert not status["mesa"]["com_peca"]
    assert all(machine["estado"] == "livre" for machine in status["maquinas"].values())


def test_reenvio_preserva_o_comando_e_nao_repete_coleta(controller, run_command):
    client, clock = controller
    run_command("ref", "referenciar_mesa")
    assert submit(client, "coleta", "coletar_peca", origem="ARMAZEM_01").status_code == 202
    duplicate = submit(client, "coleta", "coletar_peca", origem="ARMAZEM_01")
    assert duplicate.status_code == 200
    assert duplicate.json()["estado"] == "em_execucao"
    clock.advance(2)
    assert submit(client, "coleta", "coletar_peca", origem="ARMAZEM_01").json()["estado"] == (
        "concluido"
    )
    conflict = submit(client, "coleta", "coletar_peca", origem="ARMAZEM_02")
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["codigo"] == "id_em_uso"
    assert client.get("/api/status").json()["ocupacao"]["ARMAZEM_02"]


def test_maquinas_processam_em_paralelo_e_protegem_ocupacao(controller, run_command):
    client, clock = controller
    run_command("ref", "referenciar_mesa")
    run_command("coleta1", "coletar_peca", origem="ARMAZEM_01")
    run_command("deposito1", "depositar_peca", destino="M1")
    run_command("coleta2", "coletar_peca", origem="ARMAZEM_02")
    blocked = submit(client, "deposito2", "depositar_peca", destino="M1")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["codigo"] == "destino_ocupado"
    run_command("deposito2", "depositar_peca", destino="M2")
    for machine in ("M1", "M2"):
        assert (
            submit(
                client, machine, "iniciar_processamento", maquina_id=machine, duracao_ms=2000
            ).status_code
            == 202
        )
        assert client.get(f"/api/maquinas/{machine}/status").json()["tempo_restante_ms"] == 2000
    blocked = submit(client, "retirada", "coletar_peca", origem="M1")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["codigo"] == "peca_nao_disponivel"
    assert submit(client, "movimento", "mover_para", destino="QA").status_code == 202
    blocked = submit(client, "concorrente", "mover_para", destino="M3")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["codigo"] == "mesa_ocupada"
    clock.advance(2)
    for machine in ("M1", "M2"):
        assert client.get(f"/api/comandos/{machine}").json()["estado"] == "concluido"
        status = client.get(f"/api/maquinas/{machine}/status").json()
        assert status["estado"] == "aguardando_retirada"


def test_referencia_validacao_e_nova_sessao(controller):
    client, clock = controller
    original = client.get("/api/status").json()
    assert not original["mesa"]["referenciada"]
    blocked = submit(client, "mover", "mover_para", destino="M1")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["codigo"] == "mesa_sem_referencia"
    assert (
        submit(
            client, "invalid", "iniciar_processamento", maquina_id="M1", duracao_ms="500"
        ).status_code
        == 422
    )
    assert client.get("/api/maquinas/M4/status").status_code == 404
    restarted = TestClient(create_app(Simulator(initial_pieces=2, clock=clock)))
    assert restarted.get("/api/status").json()["sessao_id"] != original["sessao_id"]
    assert restarted.get("/api/comandos/mover").status_code == 404
    response = restarted.post(
        "/api/comandos",
        headers={"X-Axion-Session": original["sessao_id"]},
        json={"id": "ref", "tipo": "referenciar_mesa"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["codigo"] == "sessao_alterada"
    assert restarted.get("/api/comandos/ref").status_code == 404


def test_duas_etapas_seguidas_na_mesma_maquina(controller, run_command):
    client, _ = controller
    run_command("ref", "referenciar_mesa")
    run_command("coleta", "coletar_peca", origem="ARMAZEM_01")
    run_command("deposito", "depositar_peca", destino="M1")
    run_command("primeira", "iniciar_processamento", maquina_id="M1", duracao_ms=500)
    run_command(
        "segunda",
        "iniciar_processamento",
        maquina_id="M1",
        duracao_ms=500,
        continuar_na_maquina=True,
    )
    run_command("retirada", "coletar_peca", origem="M1")
    assert client.get("/api/maquinas/M1/status").json()["estado"] == "livre"


def test_velocidade_altera_o_relogio_sem_reiniciar_comandos(controller, run_command):
    client, clock = controller
    run_command("ref", "referenciar_mesa")
    run_command("coleta", "coletar_peca", origem="ARMAZEM")
    run_command("deposito", "depositar_peca", destino="M1")
    assert (
        submit(
            client, "processo", "iniciar_processamento", maquina_id="M1", duracao_ms=2000
        ).status_code
        == 202
    )
    clock.advance(0.5)
    assert client.post("/api/simulacao/velocidade", json={"velocidade": 0.5}).status_code == 204
    clock.advance(1)
    assert client.get("/api/maquinas/M1/status").json()["tempo_restante_ms"] == 1000
    assert client.get("/api/comandos/processo").json()["estado"] == "em_execucao"
    assert client.post("/api/simulacao/velocidade", json={"velocidade": 4}).status_code == 204
    assert submit(client, "mover", "mover_para", destino="M2").status_code == 202
    clock.advance(0.0525)
    snapshot = client.get("/api/status").json()
    assert snapshot["velocidade"] == 4
    assert abs(snapshot["mesa"]["movimento"]["progresso"] - 0.5) < 0.001
    clock.advance(0.1975)
    assert client.get("/api/comandos/processo").json()["estado"] == "concluido"
    assert client.post("/api/simulacao/velocidade", json={"velocidade": 0}).status_code == 422
    assert client.post("/api/simulacao/reset").status_code == 204
    assert client.get("/api/status").json()["velocidade"] == 1


def test_esteiras_e_estoque_auxiliar(controller, run_command):
    client, _ = controller
    run_command("ref", "referenciar_mesa")
    for index, quality in enumerate(("rejeitada", "aprovada"), start=1):
        run_command(f"coleta{index}", "coletar_peca", origem="ARMAZEM")
        snapshot = client.get("/api/status").json()
        assert snapshot["mesa"]["posicao"] == "ARMAZEM"
        assert snapshot["rfid_transportado"] == f"SIM-00{index}"
        run_command(f"buffer{index}", "depositar_peca", destino=f"B{index}")
        assert client.get("/api/status").json()["pecas"][f"B{index}"] == f"SIM-00{index}"
        run_command(f"retirada{index}", "coletar_peca", origem=f"B{index}")
        run_command(
            f"saida{index}", "depositar_peca", destino="ESTOQUE_FINAL", resultado_qa=quality
        )
    snapshot = client.get("/api/status").json()
    assert snapshot["mesa"]["posicao"] == "ESTOQUE_FINAL"
    assert snapshot["pecas"] == {"ESTOQUE_FINAL_01": "SIM-001", "ESTOQUE_FINAL_02": "SIM-002"}
    assert snapshot["resultados_qa"] == {"SIM-001": "rejeitada", "SIM-002": "aprovada"}

    assert client.post("/api/simulacao/reset").status_code == 204
    restored = client.get("/api/status").json()
    assert restored["sessao_id"] != snapshot["sessao_id"]
    assert restored["pecas"] == {"ARMAZEM_01": "SIM-001", "ARMAZEM_02": "SIM-002"}
    assert restored["resultados_qa"] == {}
    assert not restored["mesa"]["referenciada"]
    assert client.get("/api/comandos/ref").status_code == 404
