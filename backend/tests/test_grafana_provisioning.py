import json
import re

from app.config import BACKEND_DIR

ROOT = BACKEND_DIR.parent
GRAFANA_DIR = ROOT / "infrastructure" / "grafana"
DASHBOARD_PATH = GRAFANA_DIR / "dashboards" / "dados-persistidos.json"
NETWORK_DASHBOARD_PATH = GRAFANA_DIR / "dashboards" / "rede-comunicacao.json"
DATASOURCE_PATH = GRAFANA_DIR / "provisioning" / "datasources" / "postgresql.yaml"
DASHBOARD_PROVIDER_PATH = GRAFANA_DIR / "provisioning" / "dashboards" / "dashboards.yaml"


def test_grafana_dashboard_has_only_read_queries_and_required_panels() -> None:
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    assert dashboard["uid"] == "axion-dados-persistidos"
    assert dashboard["title"] == "Axion — Dados persistidos"
    assert dashboard["editable"] is False

    expected = {
        "Máquinas cadastradas",
        "Produtos cadastrados",
        "Ordens cadastradas",
        "Unidades solicitadas",
        "Unidades solicitadas por produto",
        "Composição das ordens",
        "Receitas dos produtos",
        "Carga teórica cadastrada por máquina",
    }
    panels = {panel["title"]: panel for panel in dashboard["panels"]}
    assert panels.keys() == expected

    queries = [target["rawSql"] for panel in panels.values() for target in panel["targets"]]
    assert all(query.lstrip().upper().startswith("SELECT ") for query in queries)
    forbidden = re.compile(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE)\b", re.I)
    assert all(forbidden.search(query) is None for query in queries)
    assert all(
        target["datasource"]["uid"] == "axion-postgresql"
        for panel in panels.values()
        for target in panel["targets"]
    )


def test_grafana_provisioning_uses_environment_and_read_only_mount_paths() -> None:
    datasource = DATASOURCE_PATH.read_text(encoding="utf-8")
    provider = DASHBOARD_PROVIDER_PATH.read_text(encoding="utf-8")

    assert "uid: axion-postgresql" in datasource
    assert "type: postgres" in datasource
    assert "url: database:5432" in datasource
    assert "$__env{GRAFANA_DB_USER}" in datasource
    assert "$__env{GRAFANA_DB_PASSWORD}" in datasource
    assert "$__env{POSTGRES_DB}" in datasource
    assert "grafana_reader_local" not in datasource
    assert "path: /etc/grafana/dashboards" in provider
    assert "allowUiUpdates: false" in provider


def test_network_dashboard_uses_aggregate_metrics_and_time_macros() -> None:
    dashboard = json.loads(NETWORK_DASHBOARD_PATH.read_text(encoding="utf-8"))
    assert dashboard["uid"] == "axion-rede-comunicacao"
    assert dashboard["title"] == "Axion — Rede e comunicação"
    assert dashboard["editable"] is False
    assert {panel["title"] for panel in dashboard["panels"]} == {
        "Requisições por minuto",
        "Erros por classe de status",
        "Bytes observados por conexão",
        "Latência média ponderada por conexão",
        "Retransmissões TCP por intervalo",
        "Distribuição por protocolo",
        "Disponibilidade de amostras por origem e destino",
        "Agregados recentes",
    }
    queries = [target["rawSql"] for panel in dashboard["panels"] for target in panel["targets"]]
    assert all(query.lstrip().upper().startswith("SELECT ") for query in queries)
    assert all("network_metric_samples" in query for query in queries)
    assert all("$__timeFilter(bucket_start)" in query for query in queries)
    assert "SUM(latency_sum_ms) / NULLIF(SUM(latency_count), 0)" in "\n".join(queries)
