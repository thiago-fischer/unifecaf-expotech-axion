# Backend do Axion

Implementação da SPEC-0001: cadastro, listagem e consulta de máquinas. Execução
local, sem autenticação e sem comunicação com hardware. Produtos, ordens,
otimização e estado operacional permanecem planejados.

## Ferramentas

Python **3.12 ou superior** e **uv** para instalar, resolver e executar o projeto.
Instale o uv conforme a [documentação oficial](https://docs.astral.sh/uv/getting-started/installation/).
`pyproject.toml` declara as faixas compatíveis; `uv.lock` registra as versões
exatas, inclusive dependências transitivas. Use `--locked` para reproduzi-las.

Versões resolvidas nesta entrega: FastAPI 0.141.1, SQLAlchemy 2.0.54,
Pydantic 2.13.5, Alembic 1.20.0 e Uvicorn 0.53.0. Testes usam pytest 9.1.1
e HTTPX 0.28.1; lint e formatação usam Ruff 0.16.8. A escolha de uv mantém
ambiente e dependências isolados e reproduzíveis; pytest e Ruff oferecem uma
base pequena para validar o módulo. Isso concretiza as ADRs aceitas, sem
introduzir novas decisões sobre frontend, cloud ou hardware.

## Instalação e execução

A partir da raiz do repositório, no PowerShell:

```powershell
cd backend
uv sync --locked --python 3.12
New-Item -ItemType Directory -Force data | Out-Null
uv run --locked alembic upgrade head
uv run --locked python -m app.main
```

No Linux/macOS, substitua a criação de diretório por `mkdir -p data`.
Não é necessário ativar o ambiente virtual: `uv run` usa `backend/.venv`.
Documentação interativa: [Swagger UI](http://127.0.0.1:8000/docs).
Contrato: [OpenAPI](http://127.0.0.1:8000/openapi.json).

O módulo `app.main` inicia o Uvicorn em `127.0.0.1:8000` com recarga automática
quando arquivos Python mudam. Esse modo é destinado ao desenvolvimento local.
Encerre pelo terminal com `Ctrl+C`. A CLI continua disponível como alternativa:

```powershell
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Executar `python -m app.main` inicia o servidor; importar `app.main` apenas
disponibiliza a aplicação e sua fábrica, sem iniciar o Uvicorn.

O padrão é `backend/data/axion.db`, sempre relativo ao módulo, independentemente
do diretório do terminal. A API não cria tabelas nem aplica migrations ao iniciar.
Um banco recém-preparado começa vazio. Repetir `alembic upgrade head` preserva
os registros. Dados persistem após encerrar e reiniciar o servidor.

## Execução no PyCharm

Prepare o ambiente e aplique as migrations conforme a seção anterior.
Em **Run → Edit Configurations**, adicione uma configuração **Python**:

| Campo | Valor |
|---|---|
| Nome | Axion backend |
| Execução | Module name |
| Módulo | `app.main` |
| Working directory | Caminho local da pasta `backend/` |
| Python interpreter | `backend/.venv/Scripts/python.exe` no Windows |
| Environment variables | `AXION_DATABASE_PATH`, se usar banco diferente do padrão |

Selecione essa configuração e clique em **Run**. Use **Stop** para encerrar.
O caminho do banco deve ser o mesmo usado ao executar Alembic. Em Linux/macOS,
o interpretador fica em `backend/.venv/bin/python`.

Use a execução como módulo com diretório `backend/`; não é necessário configurar
`PYTHONPATH`. Configurações pessoais da IDE e caminhos absolutos locais não
devem ser versionados. O botão Run diretamente no arquivo pode criar uma
configuração de script; nesse caso, selecione a configuração por módulo acima.

No Windows, a recarga do Uvicorn depende de sinais do console. Na validação
local, a recarga funcionou em terminal interativo, mas ficou aguardando o
processo anterior quando iniciada por subprocesso com saída redirecionada.
Se ocorrer no Run, experimente **Emulate terminal in output console**, opção
descrita na [documentação do PyCharm](https://www.jetbrains.com/help/pycharm/run-debug-configuration-python.html),
ou execute o comando na aba Terminal. O solicitante confirmou nesta entrega
que a execução no PyCharm funcionou como esperado; o uso específico da opção
de emulação de terminal não foi informado.

## Configuração do banco

API e Alembic leem `AXION_DATABASE_PATH` pela mesma configuração. Exemplo de
sobrescrita no PowerShell, antes dos comandos de migration e execução:

```powershell
$env:AXION_DATABASE_PATH = 'C:/axion-local/machines.db'
New-Item -ItemType Directory -Force 'C:/axion-local' | Out-Null
uv run --locked alembic upgrade head
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

No Linux/macOS, use `export AXION_DATABASE_PATH=/tmp/axion-local/machines.db`
e `mkdir -p /tmp/axion-local`. Caminhos relativos também são resolvidos a partir
de `backend/`. O diretório pai precisa existir e permitir escrita.
`.env.example` documenta a variável; arquivos `.env` não são lidos automaticamente.
Para voltar ao padrão no PowerShell: `Remove-Item Env:AXION_DATABASE_PATH`.

## Contrato HTTP

| Operação | Resultado |
|---|---|
| `POST /machines`, corpo `{"name":"  Máquina 1  "}` | `201`, objeto com `id` positivo e `name: "Máquina 1"` |
| `GET /machines` | `200`, array ordenado por ID (ou `[]`) |
| `GET /machines/{machine_id}` | `200`, objeto da máquina |

`name` deve ser string, com 1 a 100 caracteres após remover espaços das
extremidades. Espaços internos, acentos e capitalização são preservados.
Nomes repetidos criam IDs distintos. Campos extras são rejeitados, inclusive
`id`, `status` e tempos. Entradas inválidas retornam `422` com `detail` no
formato FastAPI/Pydantic, sem criar registros.

IDs devem representar inteiros positivos. ID inválido retorna `422`; ID positivo
inexistente retorna `404` com `{"detail":"Máquina não encontrada."}`.
Falhas SQLAlchemy retornam `500` com mensagem genérica; detalhes ficam no log
do servidor. Escritas falhas sofrem rollback. O sucesso só é retornado depois
do commit.

Exemplo em outro terminal PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/machines -ContentType 'application/json; charset=utf-8' -Body '{"name":"Máquina 1"}'
Invoke-RestMethod http://127.0.0.1:8000/machines
```

## Organização

`controllers` traduz HTTP e chama `services`; services validam as regras e
controlam commit/rollback; `repositories` consultam e executam flush.
`models` descrevem tabelas e `schemas` validam os contratos. Cada requisição
recebe uma sessão síncrona própria, encerrada ao final. O engine é descartado
no encerramento da aplicação. `create_app()` permite instâncias independentes.

## Migrations

O ambiente Alembic já está configurado em `alembic.ini`, `migrations/env.py`
e `migrations/script.py.mako`. Não execute `alembic init` em um clone: o comando
`uv run alembic init migrations` é apenas o bootstrap de um ambiente novo,
já representado pelos arquivos versionados desta entrega.

Para alterações futuras, edite o model e execute a partir de `backend/`:

```powershell
uv run --locked alembic revision --autogenerate -m "descricao da alteracao"
# Revise upgrade() e downgrade() no arquivo gerado antes de aplicar.
uv run --locked alembic upgrade head
uv run --locked alembic check
```

Versione model e migration juntos. Quem recebe a revisão pelo Git apenas
aplica `upgrade head`. Não modifique revisões já integradas.
A revisão inicial `77be86445d30` cria `machines`, com chave primária inteira
e nome obrigatório. Foi gerada por autogenerate e revisada.

`uv run --locked alembic downgrade base` remove a tabela e todos os seus dados:
execute somente em banco descartável. Os testes verificam upgrade, repetição,
downgrade e novo upgrade sem acessar o banco de desenvolvimento.

## Validação

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```

Os testes preparam bancos SQLite temporários por migrations reais e cobrem
contratos HTTP, regras do service, normalização, limites, duplicidade,
persistência após reinício, rollback de falhas simuladas e OpenAPI.
`alembic check` também verifica a coerência entre model e migration.
Nenhum teste depende da maquete; essa validação não comprova integração física.

As versões transitivas atuais emitem dois avisos de depreciação no TestClient
(HTTPX e alias BlockingPortal do AnyIO). Eles não impedem os testes e não são
suprimidos; a atualização das dependências de teste pode ser feita separadamente.
