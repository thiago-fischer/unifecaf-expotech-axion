# Controlador simulado da maquete Axion

Serviço HTTP independente que executa os seis comandos da
[SPEC-0009](../docs/specs/0009-api-controlador-maquete.md). O estado simulado
fica no serviço, com um relógio monotônico, e pode ser consultado sem abrir a
interface 3D.

## Instalação e execução

Requer Python 3.12 a 3.14 e `uv`. Na raiz do repositório, execute:

```powershell
cd controller
uv sync --locked
uv run uvicorn axion_controller.main:create_app --factory --host 127.0.0.1 --port 8001
```

Abra [Swagger UI](http://127.0.0.1:8001/docs) para enviar comandos e
[OpenAPI](http://127.0.0.1:8001/openapi.json) para consultar os schemas.
Use um único processo do Uvicorn, pois os comandos e a ocupação ficam
em memória. Cada reinício inicia uma nova sessão e restaura o cenário.
O cenário padrão tem um cubo no armazém. Para iniciar com outra quantidade,
defina `AXION_CONTROLLER_INITIAL_PIECES` entre 0 e 10 antes de subir o serviço.

## Percurso de teste

Envie cada linha em `POST /api/comandos` com um ID novo, `tipo` e
`parametros`. Consulte `GET /api/comandos/{id}` e aguarde
`concluido` antes de enviar o próximo comando da sequência.

| Tipo | Parâmetros |
|---|---|
| `referenciar_mesa` | `{}` |
| `coletar_peca` | `{"origem":"ARMAZEM_01"}` |
| `mover_para` | `{"destino":"LEITOR_RFID"}` |
| `ler_rfid` | `{"ponto":"LEITOR_RFID"}` |
| `depositar_peca` | `{"destino":"M1"}` |
| `iniciar_processamento` | `{"maquina_id":"M1","duracao_ms":500}` |
| `coletar_peca` | `{"origem":"M1"}` |
| `depositar_peca` | `{"destino":"QA"}` |
| `ler_rfid` | `{"ponto":"QA"}` |
| `coletar_peca` | `{"origem":"QA"}` |
| `depositar_peca` | `{"destino":"ESTOQUE_FINAL_01"}` |

Os dois comandos de leitura devem retornar `resultado.rfid = "SIM-001"`.
Ao final, `GET /api/status` deve indicar `ESTOQUE_FINAL_01` ocupado,
cabeçote vazio e estações livres. Nesse roteiro, quem chama a API compara
os RFIDs e decide enviar os dois últimos comandos.

## Validação

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Os testes cobrem o percurso completo, o reenvio de comandos, o paralelismo
de estações, conflitos por ocupação e a troca de sessão. O
[backend](../backend/README.md#executar-a-ordem-na-maquete-simulada) já usa
esta API para coordenar OPs simuladas. O modo conectado da cena 3D e a
execução em firmware são etapas posteriores.
