# Captura de rede do Axion

Coletor opcional da SPEC-0011. O serviço executa TShark em streaming, transforma
somente campos permitidos em eventos sanitizados e envia lotes autenticados ao
backend. Nenhum PCAP é criado.

## Execução

Na raiz do repositório, defina um token local e habilite a captura:

```powershell
$env:AXION_CAPTURE_TOKEN = 'troque-este-token-local'
$env:AXION_NETWORK_CAPTURE_ENABLED = 'true'
docker compose --profile network-lab up --build -d
docker compose --profile network-lab ps
```

Sem o profile, o serviço não é criado. Com o profile e token vazio, o coletor
encerra com uma mensagem clara e o restante do Axion continua disponível.

## Validação

```powershell
uv run --locked --project backend python -m unittest discover -s network_capture/tests -v
docker compose build network-capture
docker compose --profile network-lab logs network-capture
```

Os testes cobrem remoção de query string, normalização de rotas, correlação HTTP,
metadados PostgreSQL e descarte do próprio fluxo de ingestão.

## Limites

A captura observa frontend → backend, backend ↔ controlador e backend ↔
PostgreSQL. Ela não observa Grafana → PostgreSQL, o host inteiro, Wi-Fi ou a
futura maquete física. O laboratório usa HTTP local e não oferece
confidencialidade.
