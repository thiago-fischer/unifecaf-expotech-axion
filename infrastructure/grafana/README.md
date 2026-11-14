# Grafana do Axion

Integração local implementada pela
[SPEC-0010](../../docs/specs/0010-grafana-postgresql.md). O Grafana consulta o
PostgreSQL com uma role exclusiva e somente de leitura e apresenta cadastros e
ordens já persistidos pelo backend.

Além do dashboard de cadastros, a SPEC-0011 provisiona **Axion — Rede e
comunicação** com agregados sanitizados de tráfego. Planejamento, RFID, QA e
hardware continuam fora dos dados persistidos no Grafana.

## Componentes

- `grafana/grafana:13.3.1`: interface e execução dos dashboards.
- `grafana-db-init`: job idempotente que prepara a role PostgreSQL de leitura.
- `provisioning/datasources/postgresql.yaml`: datasource `Axion PostgreSQL`.
- `provisioning/dashboards/dashboards.yaml`: provider de dashboards.
- `dashboards/dados-persistidos.json`: dashboard inicial com oito painéis.
- `dashboards/rede-comunicacao.json`: histórico agregado de comunicação.
- volume `axion_grafana_data`: estado interno local do Grafana.

O datasource e o dashboard são versionados e montados como somente leitura. O
volume não é necessário para recriá-los.

## Configuração local

Copie o ambiente de exemplo na raiz e ajuste apenas se necessário:

```powershell
Copy-Item .env.example .env
```

Variáveis usadas:

| Variável | Uso |
|---|---|
| `GRAFANA_PORT` | Porta local, padrão `3000` |
| `GRAFANA_ADMIN_USER` | Usuário administrativo local |
| `GRAFANA_ADMIN_PASSWORD` | Senha administrativa local |
| `GRAFANA_DB_USER` | Role PostgreSQL somente leitura |
| `GRAFANA_DB_PASSWORD` | Senha da role de leitura |
| `POSTGRES_DB` | Banco consultado pelo datasource |

Os valores de `.env.example` são apenas para desenvolvimento local. Não use
essas credenciais fora desse ambiente e não versione o arquivo `.env`.

## Execução

Na raiz do repositório:

```powershell
docker compose up --build -d
docker compose ps
```

Depois que o serviço estiver saudável, acesse
<http://127.0.0.1:3000>. O dashboard fica na pasta **Axion**, com o título
**Axion — Dados persistidos**.

O fluxo de inicialização é:

```text
PostgreSQL saudável
        ↓
alembic upgrade head
        ↓
preparação da role grafana_reader
        ↓
Grafana + datasource + dashboard
```

O job de preparação é executado também para volumes PostgreSQL existentes; ele
não depende de `docker-entrypoint-initdb.d`.

## Dados apresentados

O dashboard contém:

- totais de máquinas, produtos, ordens e unidades solicitadas;
- unidades solicitadas por produto;
- carga teórica cadastrada por máquina;
- composição das ordens;
- receitas dos produtos.

A carga teórica combina quantidades solicitadas com tempos cadastrados. Ela não
representa utilização real, produtividade ou tempo executado. As tabelas atuais
não têm dimensão temporal, por isso o dashboard não cria séries históricas
artificiais.

## Validação

### Saúde e logs

```powershell
docker compose ps grafana
docker compose logs grafana-db-init
docker compose logs grafana
Invoke-RestMethod http://127.0.0.1:3000/api/health
```

O job deve encerrar com código `0` e sem imprimir senhas. A API de saúde deve
informar `database: ok`.

### Repetição da preparação

```powershell
docker compose run --rm --no-deps grafana-db-init
```

O comando pode ser repetido e também atualiza a senha da role a partir do
ambiente.

### Testes automatizados

Com o PostgreSQL local saudável:

```powershell
cd backend
$env:AXION_DATABASE_URL = 'postgresql+psycopg://axion:axion_local@127.0.0.1:5432/postgres'
$env:AXION_TEST_ADMIN_DATABASE_URL = $env:AXION_DATABASE_URL
uv run --locked pytest -q tests/test_grafana_reader.py tests/test_grafana_provisioning.py
```

Os testes criam bancos e roles descartáveis, executam todas as consultas do
dashboard e verificam que `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE` e criação de
tabela são rejeitados para a role do Grafana.

## Segurança

- Grafana e PostgreSQL publicam portas somente em `127.0.0.1` por padrão.
- Cadastro público e acesso anônimo estão desabilitados.
- O datasource usa uma role diferente da aplicação.
- A role recebe `CONNECT`, `USAGE` no schema e `SELECT` nas relações aprovadas.
- Senhas vêm do ambiente e não ficam nos arquivos de provisioning.
- `sslmode: disable` vale somente para a rede Docker local desta entrega.

O Grafana permite que administradores escrevam consultas próprias. A barreira
contra mutações está nas permissões do PostgreSQL, não apenas no dashboard.

## Reinício e rollback

Reiniciar o Grafana preserva seu estado local e reprovisiona os arquivos:

```powershell
docker compose restart grafana
```

Para parar os serviços preservando os volumes:

```powershell
docker compose down
```

Não use `docker compose down -v` se os dados do PostgreSQL ou as preferências
locais do Grafana precisarem ser preservados. A remoção da role exige revogar
seus privilégios antes de `DROP ROLE` e não faz parte do desligamento normal.
