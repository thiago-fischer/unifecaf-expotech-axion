# SPEC-0001 — Estrutura inicial do backend e cadastro de máquinas

> **Status:** Aprovada para implementação
>
> **Data:** 21/09/2026
>
> **Aprovação do escopo:** 21/09/2026, pelo responsável solicitante, nesta revisão
>
> **Implementação:** Catálogo de máquinas implementado e validado localmente;
> complemento de inicialização pelo `main.py` com Uvicorn implementado e validado
> em terminal e confirmado pelo solicitante no PyCharm. Revisão por outro integrante pendente.

### Registro de revisão — inicialização com Uvicorn

Complemento autorizado pelo responsável solicitante nesta revisão: explicitar
a inicialização local do servidor no `app/main.py` existente e sua execução
pelo terminal e pelo PyCharm. Uvicorn já consta nas dependências e a execução
pela CLI já foi validada. A execução por `python -m app.main` é o acréscimo
implementado neste complemento; as evidências anteriores não validam esse novo
caminho. Suas evidências estão registradas separadamente na seção 10.

## 1. Objetivo

Criar a base executável do backend do Axion e permitir cadastrar e consultar
as máquinas que representam as estações de processamento da maquete.

Essa entrega disponibilizará os identificadores de máquinas que serão
referenciados pelas etapas dos produtos na SPEC-0002, ainda a ser elaborada.

O escopo, as regras, os contratos e os critérios de aceite abaixo foram
aprovados para implementação. As decisões arquiteturais aceitas permanecem
como referência. Alterações posteriores de escopo devem ser registradas
e revisadas; esta aprovação não representa conclusão ou validação da entrega.

## 2. Referências e decisões existentes

- [Visão geral](../visao-geral.md): funcionamento e escopo do MVP.
- [Arquitetura](../architecture.md): componentes do sistema.
- [ADR-001](../adr/0001-python-fastapi.md): Python e FastAPI.
- [ADR-002](../adr/0002-sqlite.md): SQLite e estrutura reproduzível do banco.
- [ADR-003](../adr/0003-monorepo.md): monorepo.
- [ADR-004](../adr/0004-arquitetura-em-camadas-backend.md): arquitetura em camadas.
- [ADR-005](../adr/0005-sqlalchemy-pydantic-alembic.md): SQLAlchemy 2.x síncrono,
  schemas Pydantic separados e migrations Alembic.
- [Guia de contribuição](../../CONTRIBUTING.md): colaboração e validação.

As tecnologias acima estão aceitas. Os detalhes de ferramentas ainda não
fixados serão definidos e documentados durante a implementação, respeitando
essas decisões e o escopo aprovado.

## 3. Escopo

### Incluído

- Estrutura mínima do módulo `backend/`.
- Declaração de dependências e instruções para execução local.
- Aplicação FastAPI e registro das rotas de máquinas.
- Inicialização local com Uvicorn pelo `app/main.py` existente, com instruções
  para terminal e configuração de execução no PyCharm.
- Configuração do caminho do banco SQLite.
- Model SQLAlchemy e schemas Pydantic separados.
- Criação reproduzível da estrutura do banco com migration inicial Alembic.
- Cadastro, listagem e consulta individual de máquinas.
- Validação de entrada e respostas de erro previstas no contrato.
- Testes automatizados das regras e da integração HTTP/persistência.
- Documentação de instalação, preparação do banco, execução e testes.

### Fora desta entrega

- Edição, exclusão e desativação de máquinas.
- Cadastro de produtos, etapas e ordens de produção.
- Estado operacional, disponibilidade e filas de máquinas.
- Comunicação com firmware, sensores, motores ou displays.
- Associação entre máquina e endereço de dispositivo físico.
- Otimização, rastreabilidade, Grafana, frontend e deploy.
- Autenticação e autorização.

A execução prevista nesta entrega é local. O cadastro de uma máquina não
envia comandos à maquete nem comprova que um dispositivo está conectado.

## 4. Conceito da entidade

Uma `Machine` representa uma estação de processamento identificável no
catálogo do sistema. Seu identificador será utilizado nas receitas dos produtos.

O tempo de processamento pertence à etapa do produto: uma mesma máquina
pode executar operações com durações diferentes conforme a receita.

O cadastro não determina a posição física, a sequência das operações ou
o estado operacional da máquina. Esses conceitos serão tratados nas specs
correspondentes quando forem necessários.

### Modelo

| Campo | Tipo | Origem | Descrição |
|---|---|---|---|
| `id` | Inteiro positivo | Gerado pelo backend/banco | Identificador único e estável |
| `name` | Texto | Informado no cadastro | Nome de exibição da máquina |

Exemplo de registro retornado:

```json
{
  "id": 1,
  "name": "Máquina 1"
}
```

O ID do exemplo é ilustrativo. Clientes devem utilizar o ID retornado pela
API, sem presumir que IDs sejam consecutivos ou indiquem posição na maquete.

## 5. Regras

| Código | Regra |
|---|---|
| RN-01 | `name` é obrigatório e deve ser uma string. Não converter números, booleanos ou outros tipos em nomes. |
| RN-02 | Remover espaços em branco das extremidades do nome antes de validar e persistir. Preservar espaços internos, acentos e capitalização. |
| RN-03 | O nome normalizado deve conter entre 1 e 100 caracteres. Nomes vazios ou compostos apenas por espaços são inválidos. |
| RN-04 | O ID é gerado pelo backend/banco e não pode ser informado no cadastro. |
| RN-05 | Rejeitar campos de entrada não previstos, incluindo `id`, `status` e tempo de processamento. |
| RN-06 | Nomes repetidos são permitidos; a identidade da máquina é seu ID. |
| RN-07 | Uma criação bem-sucedida deve persistir antes de retornar sucesso. Entradas inválidas não podem criar registros. |
| RN-08 | Consultar um ID válido que não existe deve retornar recurso não encontrado. |

Não estabelecer uma quantidade fixa de máquinas nem inserir máquinas
automaticamente na inicialização. Um banco recém-preparado começa vazio.

## 6. Contrato HTTP

As rotas desta entrega não possuem prefixo de versão.

| Método e rota | Resultado | Erros previstos |
|---|---|---|
| `POST /machines` | `201 Created`, com a máquina criada | `422` para entrada inválida |
| `GET /machines` | `200 OK`, com um array de máquinas | — |
| `GET /machines/{machine_id}` | `200 OK`, com a máquina encontrada | `404` para ID inexistente; `422` para ID inválido |

### 6.1. Cadastrar máquina

Requisição para `POST /machines`:

```json
{
  "name": "Máquina 1"
}
```

Resposta `201 Created`:

```json
{
  "id": 1,
  "name": "Máquina 1"
}
```

Enviar `"  Máquina 1  "` deve resultar no nome persistido `"Máquina 1"`.
Cada POST válido cria um registro com ID próprio, inclusive se o nome repetir.

### 6.2. Listar máquinas

`GET /machines` retorna os registros em ordem crescente de ID:

```json
[
  { "id": 1, "name": "Máquina 1" },
  { "id": 2, "name": "Máquina 2" }
]
```

Sem registros, retorna `200 OK` com `[]`. Esta entrega não inclui
paginação, filtros ou busca, considerando o pequeno catálogo da maquete.

### 6.3. Consultar máquina

`GET /machines/1` retorna o mesmo formato de objeto usado na criação.
O parâmetro `machine_id` deve representar um inteiro maior que zero.

Para um ID válido inexistente, retornar `404 Not Found`:

```json
{
  "detail": "Máquina não encontrada."
}
```

### 6.4. Erros de validação e infraestrutura

- Entradas inválidas retornam `422`, usando a estrutura de validação
  de FastAPI/Pydantic, com `detail` contendo os erros e a localização do campo.
- Não fixar nesta spec o texto interno das mensagens da biblioteca.
- Erros inesperados de persistência não devem ser convertidos em `404`
  ou em sucesso. Devem produzir erro de servidor e registro para diagnóstico,
  sem expor SQL, stack traces ou caminhos internos ao cliente.

## 7. Organização

```text
backend/
├── pyproject.toml
├── README.md
├── .env.example
├── alembic.ini
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── <revision>_create_machines.py
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── controllers/
│   │   └── machine_controller.py
│   ├── services/
│   │   └── machine_service.py
│   ├── repositories/
│   │   └── machine_repository.py
│   ├── models/
│   │   └── machine.py
│   ├── schemas/
│   │   └── machine_schema.py
│   └── database/
│       ├── base.py
│       └── database.py
└── tests/
    ├── conftest.py
    ├── test_machine_service.py
    ├── test_machine_api.py
    └── test_migrations.py
```

Adicionar `__init__.py` aos pacotes conforme necessário. `<revision>` representa
o identificador gerado pelo Alembic, não um nome literal de arquivo.
Não criar antecipadamente módulos de produtos ou outras funcionalidades.

### Responsabilidades

- `main.py`: compor a aplicação, registrar as rotas e iniciar o Uvicorn somente
  quando executado como programa, sob `if __name__ == "__main__":`.
  Importar `app.main` deve continuar disponibilizando `app` e `create_app()`
  sem abrir uma porta ou iniciar processos do servidor.
- `config.py`: centralizar a configuração, incluindo o caminho do SQLite.
- Controller: receber a entrada, chamar o service e mapear resultados/erros
  para HTTP. Não executar consultas ao banco.
- Service: aplicar regras de domínio, coordenar repositories e commit/rollback
  da operação completa, sem depender de objetos de requisição ou exceções HTTP.
- Repository: persistir e consultar máquinas com SQLAlchemy; pode executar
  flush, mas não commit independente.
- Model: representar a tabela usando a API declarativa tipada do SQLAlchemy 2.x.
- Schemas Pydantic: definir entrada e saída; validar tipo, campos e limites
  declarados, separados do model SQLAlchemy.
- Database: configurar engine e fábrica de sessões síncronas; fornecer uma
  sessão por requisição que acessar o banco e encerrá-la ao final.
- `base.py`: definir a base declarativa compartilhada dos models.
- `migrations/env.py`: carregar configuração e metadados dos models para o Alembic.

Além da base declarativa exigida pelo mapeamento adotado, não é necessário
criar classes-base de serviços ou repositories genéricos para esta entrega.
Usar rotas/dependências síncronas para esse fluxo de acesso ao banco.

## 8. Persistência e ambiente

- Criar por migration Alembic uma tabela `machines`, com `id` como chave
  primária e `name` obrigatório, alinhada ao model SQLAlchemy.
- Configuração: variável `AXION_DATABASE_PATH`, com padrão local
  `backend/data/axion.db`, resolvido em relação ao módulo e não ao diretório
  de onde o terminal foi aberto.
- Documentar como substituir o caminho do banco e preparar seu diretório.
- Manter dados após reiniciar a aplicação.
- Preparar um banco vazio aplicando o histórico de migrations com
  `alembic upgrade head`, a partir de `backend/`.
- Reexecutar a preparação não deve apagar dados nem duplicar a estrutura.
- Não recriar ou limpar o banco durante a inicialização normal da API,
  nem executar `create_all()` ou migrations automaticamente nesse momento.
- Encerrar conexões/sessões corretamente e desfazer transações que falharem.
- Usar banco temporário isolado nos testes, sem acessar o banco de desenvolvimento.
- Ignorar no Git bancos locais, arquivos auxiliares do SQLite, `.env`, ambiente
  virtual e caches. Versionar somente configuração de exemplo sem segredos.

API e Alembic devem derivar a conexão da mesma configuração, incluindo a
sobrescrita de `AXION_DATABASE_PATH` usada nos testes. Não manter caminhos
independentes que possam atualizar um banco diferente daquele usado pela API.

### Fluxo de migrations

Depois de configurar o ambiente Alembic, o fluxo de desenvolvimento será:

1. Alterar o model SQLAlchemy.
2. Gerar uma revisão com `alembic revision --autogenerate -m "create machines"`
   (mensagem ilustrativa para a primeira revisão).
3. Revisar `upgrade()` e `downgrade()` antes de aplicar a revisão.
4. Aplicar `alembic upgrade head` ao banco de desenvolvimento.
5. Versionar a migration junto com a alteração do model.

Quem recebe a alteração pelo Git aplica as revisões existentes com
`alembic upgrade head`; não gera novamente a migration.
O autogenerate compara o banco com os metadados e pode exigir correções
manuais; gerar uma revisão não aplica a alteração ao banco.

A migration inicial deve possuir `upgrade()` para criar `machines` e
`downgrade()` para removê-la. Sua reversão elimina os dados dessa tabela;
testar `alembic downgrade base` somente em banco descartável.
Essa reversão não faz parte da inicialização normal da aplicação.

### Inicialização local com Uvicorn

Complementar `backend/app/main.py`, preservando `app` e `create_app()`.
Não criar `server.py` nem outra spec para esse complemento. A chamada
`uvicorn.run()` deve ficar protegida por `if __name__ == "__main__":`,
utilizando a referência de importação `"app.main:app"`, host `127.0.0.1`,
porta `8000` e `reload=True` para desenvolvimento local.

O modo com recarga não constitui configuração de produção. Deploy, workers,
Docker e exposição em rede permanecem fora desta entrega.

O fluxo implementado e documentado a partir da raiz do repositório,
no PowerShell, é:

```powershell
cd backend
uv sync --locked --python 3.12
New-Item -ItemType Directory -Force data | Out-Null
uv run --locked alembic upgrade head
uv run --locked python -m app.main
```

A execução pela CLI já existente deverá continuar funcionando:

```powershell
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

As duas formas devem disponibilizar `/docs`, `/openapi.json` e as três rotas
de máquinas em `http://127.0.0.1:8000`, usando a configuração compartilhada de
banco. Iniciar ou recarregar o servidor não deve aplicar migrations, criar
tabelas nem inserir registros. A preparação do banco permanece explícita.

Documentar no README do backend uma configuração Python do PyCharm:

| Campo | Valor |
|---|---|
| Execução | Módulo (`Module name`) |
| Módulo | `app.main` |
| Diretório de trabalho | Caminho local da pasta `backend/` |
| Interpretador no Windows | `backend/.venv/Scripts/python.exe` |
| Variáveis de ambiente | `AXION_DATABASE_PATH`, somente se houver sobrescrita |

O botão Run dessa configuração deverá iniciar o servidor. O fluxo documentado
usa execução como módulo, sem exigir executar `app/main.py` como arquivo avulso
ou modificar manualmente o `PYTHONPATH`. Não versionar caminhos absolutos da
máquina do desenvolvedor nem configurações pessoais da IDE.

## 9. Critérios de aceite

A aprovação desta spec autoriza sua implementação. Os itens abaixo só
devem ser marcados após implementação e verificação, com evidências dos
testes ou validações registradas no Pull Request. A entrega estará concluída
quando todos os critérios forem atendidos e a revisão prevista no guia de
contribuição for realizada.

- [x] CA-01: A partir de um clone limpo, o README permite instalar dependências,
  preparar o banco e iniciar o backend localmente.
- [x] CA-02: A documentação OpenAPI apresenta as três rotas, schemas e respostas previstas.
- [x] CA-03: Cadastrar um nome válido retorna `201`, um ID positivo e o nome normalizado.
- [x] CA-04: Nomes com 1 e 100 caracteres após normalização são aceitos.
- [x] CA-05: Nome ausente, nulo, vazio, somente espaços, de tipo incorreto ou
  acima de 100 caracteres retorna `422` e não cria registro.
- [x] CA-06: Enviar campos extras, incluindo um ID definido pelo cliente,
  retorna `422` e não cria registro.
- [x] CA-07: Dois cadastros com o mesmo nome recebem IDs distintos, conforme RN-06.
- [x] CA-08: Listar um banco vazio retorna `[]`; após cadastros, retorna os
  registros em ordem crescente de ID.
- [x] CA-09: Consultar uma máquina cadastrada retorna `200` com seus dados;
  consultar ID positivo inexistente retorna `404` com o contrato definido.
- [x] CA-10: Consultar com ID zero, negativo ou não inteiro retorna `422`.
- [x] CA-11: Uma máquina continua disponível depois de reiniciar a aplicação
  usando o mesmo arquivo SQLite.
- [x] CA-12: `alembic upgrade head` prepara um banco vazio; repetir o comando
  na mesma revisão preserva os registros e não duplica a estrutura.
- [x] CA-13: Uma falha de persistência não retorna `201`, não deixa gravação
  parcial e não expõe detalhes internos na resposta.
- [x] CA-14: Testes utilizam banco isolado e podem ser executados sem hardware.
- [x] CA-15: Controllers, services e repositories respeitam a separação da ADR-004.
- [x] CA-16: Em banco descartável, a migration inicial permite executar
  upgrade, downgrade até base e novo upgrade com sucesso.
- [x] CA-17: A API e o Alembic utilizam o mesmo banco quando o caminho é
  sobrescrito; o teste não altera o banco de desenvolvimento.
- [x] CA-18: Os testes de integração preparam seu banco pelas migrations e
  validam que o model consegue ler e gravar na estrutura criada por elas.
- [x] CA-19: Com banco preparado, `uv run --locked python -m app.main`, a partir
  de `backend/`, inicia o Uvicorn em `127.0.0.1:8000`; `/docs`, `/openapi.json`
  e as três rotas de máquinas respondem conforme o contrato.
- [x] CA-20: Importar `app.main` disponibiliza `app` e `create_app()` sem iniciar
  o Uvicorn, abrir porta ou disparar processos de recarga.
- [x] CA-21: Alterar um arquivo Python observado pelo servidor provoca recarga;
  a API volta a responder e preserva os registros no mesmo SQLite. Encerrar
  e reiniciar pelo novo ponto de entrada também preserva esses registros.
- [x] CA-22: O README permite iniciar o servidor pelo Run do PyCharm usando
  o módulo `app.main`, o interpretador do backend e o diretório de trabalho
  indicado, sem ajustes manuais de `PYTHONPATH`.
- [x] CA-23: A CLI Uvicorn existente continua funcional; iniciar ou recarregar
  pelo novo ponto de entrada não aplica migrations, cria tabelas ou insere dados.
- [x] CA-24: Testes automatizados, lint e formatação do backend continuam
  passando após o complemento; evidências da execução real, recarga e PyCharm
  são registradas separadamente das evidências anteriores.

## 10. Plano de implementação e validação

1. Selecionar e documentar as versões e ferramentas de desenvolvimento pendentes.
2. Criar o módulo, dependências, configuração e ponto de entrada FastAPI.
3. Implementar o model SQLAlchemy, configurar Alembic, revisar a migration
   inicial e implementar o repository.
4. Implementar schemas, service, controller e registro das rotas.
5. Cobrir os critérios relevantes com testes de regras e integração HTTP/SQLite.
6. Validar migrations em banco descartável, persistência após reinicialização
   e instruções do README.
7. Revisar o diff, a documentação e abrir Pull Request conforme CONTRIBUTING.md.

Os comandos de instalação, configuração inicial do Alembic, preparação,
execução e testes estão documentados em [backend/README.md](../../backend/README.md).

### Plano do complemento Uvicorn

1. Acrescentar ao `app/main.py` o bloco protegido de inicialização descrito na
   seção 8, mantendo a composição da aplicação e o ciclo de vida existentes.
2. Atualizar o README com a execução por módulo e a configuração do PyCharm,
   preservando as instruções da CLI e a etapa explícita de migrations.
3. Verificar a importação sem inicialização do servidor e executar testes,
   lint e formatação pertinentes.
4. Em banco descartável preparado por Alembic, validar HTTP real pelo novo
   ponto de entrada, recarga, reinício, persistência e execução pelo PyCharm.
   Usar o mesmo caminho de banco na migration e no servidor.
5. Registrar as evidências no Pull Request e marcar CA-19 a CA-24 somente
   após verificação. CA-22 e a parte de validação na IDE de CA-24 foram concluídos
   com a confirmação de funcionamento pelo solicitante.

### Evidências do complemento Uvicorn

- `app/main.py` inicia o servidor sob guarda `__main__`, preservando a fábrica
  e a aplicação importável. O README documenta a execução por módulo e a IDE.
- **44 testes passaram** no ambiente do backend com Python 3.13.13, incluindo
  um novo teste que importa a aplicação em processo isolado, impede chamada
  a `uvicorn.run()` e verifica que nenhum arquivo de banco foi criado.
  Ruff (lint e formatação) passou. Permanecem os dois avisos de depreciação
  das dependências de teste já documentados.
- CA-19: `uv run --locked python -m app.main` executado em terminal na pasta
  `backend/`, com `AXION_DATABASE_PATH` apontando para banco descartável.
  `/docs`, `/openapi.json`, POST, listagem e consulta individual validados
  por HTTP real; nome normalizado e resposta `201` conferidos.
- CA-21: em cópia descartável do código, alterar `app/main.py` encerrou o
  processo anterior e iniciou outro, confirmado pelos logs e IDs de processo.
  Após a recarga, a API preservou o único cadastro. Encerramento com `Ctrl+C`
  e reinício por módulo também preservaram o cadastro.
- CA-23: iniciar e recarregar sem migrations manteve o arquivo SQLite ausente.
  Depois da preparação explícita com Alembic, recarga e reinício preservaram
  os dados sem inserir registros adicionais. A CLI anterior foi executada
  novamente e consultou o mesmo registro persistido.
- Limitação observada: no Windows, a tentativa por subprocesso com saída
  redirecionada detectou a alteração, mas aguardou o encerramento do processo
  anterior. A recarga passou ao repetir em terminal interativo. O README
  registra essa limitação e a opção de emulação de terminal do PyCharm como
  alternativa a verificar, sem afirmar que já foi testada na IDE.
- CA-22 e CA-24: instruções da IDE documentadas; execução como módulo sem
  `PYTHONPATH` validada em terminal. Após a entrega, o solicitante confirmou
  nesta conversa: "testei aqui e funcionou da forma que esperava".
  A validação na IDE é relatada pelo solicitante, não executada pelo agente;
  o uso da opção de emulação de terminal não foi informado. Essa confirmação
  conclui a pendência da IDE, junto aos testes, lint e formatação já executados.
  Nenhuma validação em hardware foi realizada.

### Evidências da implementação — 21/09/2026

- CA-01: instalação com `uv sync --locked --python 3.12`, criação do diretório
  e `alembic upgrade head` em cópia limpa, sem ambiente virtual anterior.
  Uvicorn iniciado e consultado por HTTP real em endereço local.
- CA-02 a CA-10 e CA-13: `test_machine_api.py` cobre OpenAPI, contratos,
  limites, campos extras, IDs, duplicidade e falhas simuladas de flush,
  commit e consulta; `test_machine_service.py` valida regras fora de HTTP
  e rollback após flush, incluindo reutilização da sessão.
- CA-11: testes com duas instâncias da aplicação e smoke test HTTP com
  encerramento e reinicialização de processos Uvicorn usando o mesmo arquivo.
- CA-12, CA-16 e CA-17: `test_migrations.py` verifica repetição de upgrade,
  preservação dos registros, downgrade/base, novo upgrade, configuração
  compartilhada e independência do diretório de execução.
- CA-14 e CA-18: fixtures aplicam migrations em arquivos temporários isolados;
  os testes de integração leem e gravam com o model sobre essas tabelas.
- CA-15: revisão local das camadas; controllers chamam services, repositories
  concentram consultas e flush, services controlam commit/rollback.
- Resultado: **43 testes passaram em Python 3.12.13 e 3.13.13**;
  `ruff check .`, `ruff format --check .` e coerência Alembic/model passaram.
  Dois avisos de depreciação das dependências de teste estão documentados no
  README do backend. Nenhuma validação em hardware foi realizada.

Os critérios marcados representam verificação local. A conclusão da entrega
continua dependendo da revisão de outro integrante no Pull Request, conforme
CONTRIBUTING.md.

## 11. Decisões aprovadas e detalhes de implementação

| Ponto | Definição |
|---|---|
| Identidade | ID inteiro gerado pelo banco; nome apenas para exibição |
| Nomes duplicados | Permitidos nesta entrega |
| Limite do nome | 100 caracteres após remover espaços das extremidades |
| Listagem | Array completo, ordenado por ID, sem paginação inicial |
| Ferramentas | Python 3.12+, uv e uv.lock; pytest/HTTPX e Ruff; versões documentadas no README do backend |
| Servidor local | Uvicorn; inicialização em `app/main.py` sob guarda `__main__`, referência `app.main:app`, host `127.0.0.1`, porta `8000` e recarga para desenvolvimento |
| Configuração | `AXION_DATABASE_PATH`, com padrão local `backend/data/axion.db`, conforme seção 8 |

Mudanças arquiteturais relevantes durante a implementação devem ser registradas
em ADR. A implementação da SPEC-0002 deverá usar os IDs deste catálogo para
validar as máquinas referenciadas nas etapas dos produtos.
