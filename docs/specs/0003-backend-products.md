# SPEC-0003 — Cadastro de produtos e etapas produtivas

> **Status:** Implementada; revisão de PR pendente
>
> **Data:** 29/09/2026
>
> **Implementação:** Concluída em 02/10/2026, com validação local automatizada.

## 1. Objetivo

Permitir cadastrar e consultar produtos personalizados no backend do Axion,
definindo o nome e a receita de produção: uma sequência de etapas, cada uma
associada a uma máquina cadastrada e a um tempo de processamento.

Essa entrega fornecerá os produtos que poderão ser referenciados por futuras
ordens de produção. Criar um produto apenas registra sua receita; não inicia
produção, não reserva máquinas e não cria unidades físicas.

As regras e os contratos abaixo foram implementados por solicitação do responsável.
As ADRs aceitas permanecem obrigatórias; a revisão por outro integrante no PR
continua necessária antes do merge.

## 2. Referências e contexto atual

- [Visão geral](../visao-geral.md): produtos configuráveis, etapas e ordens.
- [Arquitetura](../architecture.md): componentes e tecnologias.
- [Exemplo de produto](../examples/product.json): formato inicial da receita.
- [SPEC-0001](0001-backend-machines.md): catálogo de máquinas implementado e IDs
  usados pelas etapas dos produtos.
- [SPEC-0002](0002-ci-testes-automatizados.md): execução da suíte do backend na CI.
- [ADR-001](../adr/0001-python-fastapi.md): Python e FastAPI.
- [ADR-002](../adr/0002-sqlite.md): SQLite.
- [ADR-003](../adr/0003-monorepo.md): monorepo.
- [ADR-004](../adr/0004-arquitetura-em-camadas-backend.md): camadas do backend.
- [ADR-005](../adr/0005-sqlalchemy-pydantic-alembic.md): SQLAlchemy 2.x síncrono,
  schemas Pydantic separados, migrations Alembic e transação de produto e etapas.
- [README do backend](../../backend/README.md): execução e validação existentes.
- [Guia de contribuição](../../CONTRIBUTING.md): branches, PRs e revisão.

O backend já possui configuração de banco, sessões por requisição, cadastro e
consulta de máquinas, migrations e testes. Esta entrega estende essa estrutura.
O exemplo de produto orienta os nomes dos campos, mas não define sozinho regras
de validação, respostas HTTP ou uma funcionalidade já disponível.

## 3. Escopo

### Incluído

- Cadastro de produto com todas as suas etapas em uma única operação atômica.
- Listagem de produtos e consulta individual, incluindo a receita completa.
- Validação da sequência, dos tempos e da existência das máquinas referenciadas.
- Models SQLAlchemy e schemas Pydantic para produto e etapas.
- Nova migration para produtos, etapas e suas restrições de integridade.
- Testes das regras, contratos HTTP, persistência e migrations.
- Atualização do README do backend e do estado de implementação na documentação.

### Fora desta entrega

- Edição, exclusão, desativação, cópia e versionamento de receitas.
- Endpoints independentes para cadastrar ou alterar etapas.
- Ordens de produção, quantidades, estoque e identificação de unidades físicas.
- Otimização, cálculo do tempo total de uma ordem e reserva de máquinas.
- Etapas paralelas, máquinas alternativas e tempos de transporte ou preparação.
- Estado operacional das máquinas, execução física e comunicação com firmware.
- Frontend, autenticação, autorização, Grafana e deploy.

Produtos cadastrados pelo usuário pertencem ao mesmo catálogo, sem categoria
técnica separada para produtos personalizados. Em complemento posterior a esta
entrega, por solicitação do responsável em 02/10/2026, a revisão `bb94b7e72eb7`
passou a inserir três produtos base em contexto CNC. Receitas, tempos simulados
e comportamento de aplicação/reversão estão no
[README do backend](../../backend/README.md#dados-iniciais). A carga ocorre pela
migration explícita, sem inserções na inicialização da API.

## 4. Conceito das entidades

Uma `Product` representa uma receita reutilizável de produção. Sua identidade
é o ID, e não o nome. Uma `ProductStep` representa uma operação dessa receita.
O tempo pertence à etapa do produto, conforme a SPEC-0001; não à máquina.

### Produto

| Campo | Tipo | Origem | Descrição |
|---|---|---|---|
| `id` | Inteiro positivo | Backend/banco | Identificador único do produto |
| `name` | Texto | Cadastro | Nome de exibição |
| `steps` | Lista de etapas | Cadastro | Receita com ao menos uma etapa |

### Etapa

| Campo | Tipo | Origem | Descrição |
|---|---|---|---|
| `sequence` | Inteiro positivo | Cadastro | Posição da etapa, iniciando em 1 |
| `machine_id` | Inteiro positivo | Cadastro | Referência a uma máquina existente |
| `processing_time_seconds` | Inteiro positivo | Cadastro | Duração planejada em segundos inteiros |

A identidade da etapa é o par `(product_id, sequence)`. `product_id` é definido
internamente pelo produto criado; não é enviado no corpo nem repetido em cada
etapa da resposta. Não há ID independente de etapa nesta entrega.

Uma máquina pode aparecer em várias etapas, inclusive consecutivas, com tempos
diferentes. A sequência indica precedência dentro da receita, sem determinar
horários de execução nem comprovar a viabilidade física do percurso na maquete.

## 5. Regras

| Código | Regra |
|---|---|
| RN-01 | `name` é obrigatório e deve ser string, sem converter outros tipos em texto. |
| RN-02 | Remover espaços em branco das extremidades antes de validar e persistir; preservar espaços internos, acentos e capitalização. |
| RN-03 | O nome normalizado deve conter entre 1 e 100 caracteres. Nomes repetidos são permitidos, com IDs distintos. |
| RN-04 | `steps` é obrigatório e deve ser uma lista não vazia de objetos de etapa. |
| RN-05 | Cada etapa deve informar os três campos do contrato. Valores nulos e campos extras são rejeitados, tanto no produto quanto nas etapas, incluindo `id` e `product_id`. |
| RN-06 | `sequence`, `machine_id` e `processing_time_seconds` devem ser inteiros JSON maiores que zero. Rejeitar booleanos, strings numéricas e números decimais, inclusive `1.0`, sem coerção. |
| RN-07 | Para N etapas, as sequências devem formar exatamente o conjunto de 1 a N, sem repetição ou lacunas. |
| RN-08 | `sequence` determina a ordem, independentemente da posição no array recebido. Aceitar arrays fora de ordem e retornar as etapas ordenadas por sequência. Não renumerar entradas inválidas. |
| RN-09 | Todas as máquinas referenciadas devem existir. Uma referência inexistente invalida o cadastro inteiro. Não criar máquinas implicitamente. |
| RN-10 | Permitir a repetição de `machine_id` na receita. Não exigir que todas as máquinas do catálogo sejam utilizadas. |
| RN-11 | Produto e etapas devem ser persistidos na mesma transação. Retornar sucesso somente após commit; qualquer falha deve desfazer toda a gravação. |
| RN-12 | Consultar um ID de produto válido inexistente retorna recurso não encontrado. |
| RN-13 | Quantidade e identidade de unidades físicas não pertencem ao produto. Não aceitar esses campos no cadastro. |

Não impor quantidade fixa de produtos ou etapas nesta entrega. O tempo
informado é uma duração planejada positiva; não há cronômetro ou simulação
de execução neste cadastro. A soma das durações não representa o tempo total
de uma ordem e não será incluída como campo calculado.

## 6. Contrato HTTP

Manter o padrão de rotas sem prefixo de versão utilizado para máquinas.

| Método e rota | Resultado | Erros previstos |
|---|---|---|
| `POST /products` | `201 Created`, produto com suas etapas | `422` para entrada ou receita inválida |
| `GET /products` | `200 OK`, array de produtos completos | — |
| `GET /products/{product_id}` | `200 OK`, produto com suas etapas | `404` para ID inexistente; `422` para ID inválido |

### 6.1. Cadastrar produto

Requisição para `POST /products`, compatível com o exemplo já existente:

```json
{
  "name": "Produto A",
  "steps": [
    { "sequence": 1, "machine_id": 2, "processing_time_seconds": 10 },
    { "sequence": 2, "machine_id": 1, "processing_time_seconds": 15 },
    { "sequence": 3, "machine_id": 3, "processing_time_seconds": 8 }
  ]
}
```

Resposta `201 Created`:

```json
{
  "id": 1,
  "name": "Produto A",
  "steps": [
    { "sequence": 1, "machine_id": 2, "processing_time_seconds": 10 },
    { "sequence": 2, "machine_id": 1, "processing_time_seconds": 15 },
    { "sequence": 3, "machine_id": 3, "processing_time_seconds": 8 }
  ]
}
```

Os IDs são ilustrativos. Antes do cadastro, obter os IDs reais pelo catálogo
de máquinas; os três IDs referenciados precisam existir. Cada POST válido
cria um produto com identidade própria, inclusive quando a receita e o nome
se repetem. Enviar `"  Produto A  "` persiste `"Produto A"`.

### 6.2. Listar e consultar produtos

`GET /products` retorna um array no formato dos objetos da criação, em ordem
crescente de ID de produto, com etapas em ordem crescente de `sequence`.
Sem registros, retorna `200 OK` com `[]`. Não inclui paginação, filtros ou busca
nesta entrega, considerando o pequeno catálogo inicial.

`GET /products/{product_id}` retorna o mesmo objeto usado na criação.
O parâmetro de caminho deve representar um inteiro maior que zero; valores
zero, negativos ou não inteiros retornam `422`.

Para um ID positivo inexistente, retornar `404 Not Found`:

```json
{ "detail": "Produto não encontrado." }
```

### 6.3. Erros de validação e infraestrutura

- Erros de tipos, obrigatoriedade, limites e campos extras retornam `422`,
  com `detail` no formato de validação FastAPI/Pydantic e localização do campo.
  Não fixar o texto interno das mensagens da biblioteca.
- Sequências repetidas ou com lacunas retornam `422` com
  `{"detail":"As sequências das etapas devem ser únicas e consecutivas, de 1 a N."}`.
- Máquinas inexistentes retornam `422` com o contrato abaixo. A lista contém
  todos os IDs ausentes, sem repetição e em ordem crescente:

```json
{
  "detail": "Uma ou mais máquinas das etapas não existem.",
  "machine_ids": [9, 12]
}
```

A referência inválida na criação é um erro da receita; o `404` fica reservado
à consulta de produto inexistente. Validar estrutura e tipos primeiro,
sequências depois e existência das máquinas por último; não é necessário
agrupar erros de fases diferentes na mesma resposta.

Falhas inesperadas de persistência seguem o tratamento de erro de servidor
existente, com rollback e diagnóstico no log, sem expor SQL, caminhos internos
ou stack traces ao cliente. Não converter qualquer erro de banco em `422`.

## 7. Organização

Arquivos adicionados à estrutura existente nesta entrega:

```text
backend/
├── app/
│   ├── controllers/product_controller.py
│   ├── services/product_service.py
│   ├── repositories/product_repository.py
│   ├── models/product.py
│   ├── models/product_step.py
│   └── schemas/product_schema.py
├── migrations/versions/<revision>_create_products_and_steps.py
└── tests/
    ├── test_product_service.py
    ├── test_product_api.py
    └── test_migrations.py
```

- Controller: receber requisições, chamar o service e mapear erros de domínio
  para as respostas HTTP; não consultar o banco diretamente.
- Service: validar a receita também para chamadas fora de HTTP, consultar
  máquinas por repository e coordenar commit/rollback de produto e etapas.
- Repositories: consultar e persistir usando a mesma sessão da operação;
  permitir flush, sem commits independentes. Estender `MachineRepository`
  para consultar os IDs necessários caso isso simplifique a validação.
- Models: representar produto, etapas, relacionamentos e restrições.
- Schemas: separar contratos de criação e leitura dos models SQLAlchemy.
- Integração: registrar rotas no `main.py` e carregar os novos models nos
  metadados usados pelo Alembic, mantendo os padrões existentes.

Reutilizar configuração, base declarativa, sessões síncronas e fixtures de
teste. Não criar uma segunda infraestrutura de banco nem classes-base genéricas.

## 8. Persistência e ambiente

Criar uma nova revisão Alembic após a revisão atual `77be86445d30`, sem alterar
a migration de máquinas já integrada. Se o histórico avançar antes da
implementação, encadear a revisão ao head efetivo e revisar a compatibilidade.

| Tabela | Colunas e restrições |
|---|---|
| `products` | `id` inteiro, chave primária gerada; `name` texto obrigatório |
| `product_steps` | `product_id`, `sequence`, `machine_id` e `processing_time_seconds` inteiros obrigatórios; chave primária composta por `(product_id, sequence)` |

- `product_steps.product_id` referencia `products.id` e `machine_id` referencia
  `machines.id`. Não permitir exclusão de registros referenciados; não introduzir
  exclusão em cascata de receitas ao remover uma máquina.
- Definir CHECKs para `sequence > 0` e `processing_time_seconds > 0`.
  A continuidade da sequência é validada pelo service sobre a receita completa.
- Garantir que as chaves estrangeiras sejam efetivamente habilitadas em cada
  conexão SQLite (`PRAGMA foreign_keys=ON`), na API, no Alembic e nos testes.
  Essa ativação está implementada no `build_engine` compartilhado.
- Carregar e retornar etapas ordenadas explicitamente, sem depender da ordem
  física de inserção ou leitura do banco.
- Preservar máquinas e seus IDs ao aplicar a nova revisão em banco existente.
- Continuar usando `AXION_DATABASE_PATH` compartilhado entre API e Alembic.
- Preparar e atualizar o banco explicitamente com `alembic upgrade head`;
  não usar `create_all()` nem migrations automáticas ao iniciar a API.
- O downgrade desta revisão remove primeiro `product_steps`, depois `products`,
  eliminando produtos e receitas, mas preservando `machines`. Testar reversão
  somente em banco descartável; ela não restaura dados removidos.

## 9. Critérios de aceite

Itens verificados localmente por testes automatizados e revisão das camadas. Registrar
as evidências no PR; o merge exige revisão de outro integrante.

- [x] CA-01: OpenAPI apresenta as três rotas, schemas e respostas previstas.
- [x] CA-02: Cadastro válido retorna `201`, ID positivo, nome normalizado e
  etapas completas; uma receita com apenas uma etapa é aceita.
- [x] CA-03: Nomes com 1 e 100 caracteres após normalização são aceitos;
  nomes ausentes, nulos, vazios, só espaços, de tipo errado ou longos retornam `422`.
- [x] CA-04: Nomes e receitas repetidos geram produtos com IDs diferentes.
- [x] CA-05: `steps` ausente, nulo, vazio ou de tipo incorreto, etapas que não
  são objetos, campos ausentes e campos extras retornam `422`, sem gravação.
- [x] CA-06: Campos inteiros das etapas rejeitam zero, negativos, nulos,
  booleanos, strings e decimais, inclusive `1.0`, sem gravar produto ou etapas.
- [x] CA-07: Sequências repetidas, iniciadas acima de 1 ou com lacunas retornam
  o erro definido; arrays fora de ordem são aceitos e retornados ordenados.
- [x] CA-08: Máquinas inexistentes produzem `422` com todos os IDs ausentes
  ordenados e sem duplicatas; nenhuma parte do produto é persistida.
- [x] CA-09: Uma máquina pode aparecer em várias etapas com tempos distintos.
- [x] CA-10: Listagem vazia retorna `[]`; demais listagens ordenam produtos por
  ID e etapas por sequência, sem perder ou duplicar etapas.
- [x] CA-11: Consulta existente retorna a receita completa; ID positivo ausente
  retorna o `404` previsto; IDs inválidos retornam `422`.
- [x] CA-12: Produto e etapas permanecem disponíveis após reiniciar a aplicação
  usando o mesmo banco.
- [x] CA-13: Falha simulada após flush parcial e falha de commit desfazem toda
  a criação, sem deixar produto ou etapas, sem retornar sucesso ou expor detalhes.
- [x] CA-14: A nova migration funciona em banco vazio e em banco com máquinas;
  repetir upgrade preserva os dados, inclusive produtos já cadastrados.
- [x] CA-15: Em banco descartável, downgrade à revisão anterior preserva as
  máquinas; novo upgrade funciona e `alembic check` não detecta divergências.
- [x] CA-16: Testes comprovam a rejeição de referências órfãs, sequência
  duplicada no mesmo produto e valores não positivos cobertos por CHECKs,
  inclusive em escritas diretas de teste que não passam pelo service.
- [x] CA-17: Services validam a receita fora de HTTP; controllers e repositories
  mantêm as responsabilidades das ADRs 004 e 005.
- [x] CA-18: A suíte completa, lint e formatação passam; testes usam SQLite
  temporário preparado por migrations, sem banco de desenvolvimento ou hardware.
- [x] CA-19: README do backend documenta cadastro e consulta com IDs reais de
  máquinas, erros, preparação do banco e comandos de validação.

## 10. Plano de implementação e validação

1. Revisar o escopo e as propostas da seção 11 antes da implementação.
2. Criar models e schemas; registrar metadados e preparar a nova migration.
3. Habilitar e testar a integridade referencial nas conexões compartilhadas.
4. Implementar repositories, service transacional e controller; registrar rotas.
5. Cobrir as regras e os contratos com testes, incluindo rollback após escrita
   parcial, preservação das máquinas e migração de banco existente.
6. Atualizar o README do backend e indicar nos documentos gerais somente o
   comportamento efetivamente implementado e validado.
7. Executar a suíte e as verificações locais; registrar resultados e obter
   revisão no PR, acompanhando o check existente da SPEC-0002.

Comandos para reproduzir a validação, a partir de `backend/`:

```powershell
uv sync --locked --python 3.12
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```

Validar `uv run --locked alembic upgrade head` e
`uv run --locked alembic check` com `AXION_DATABASE_PATH` apontando para um banco
descartável cujo diretório já exista. Os testes de migration também devem
exercitar upgrade a partir da revisão de máquinas com dados existentes e
reversão até ela. A validação manual pode usar `/docs` para cadastrar máquinas,
obter seus IDs, cadastrar produto e consultar sua receita.

### Evidências da implementação

Validação local em 02/10/2026: 129 testes passaram; Ruff lint e formatação
passaram. Upgrade e alembic check foram executados em banco descartável.
A suíte cobre contratos HTTP, services fora de HTTP, rollback após flush parcial
e falha de commit, integridade por SQL direto, reinício, upgrade de banco existente
e downgrade preservando máquinas. Há dois avisos de depreciação já existentes
nas dependências de teste. A revisão no PR permanece pendente; não houve
validação em hardware e os testes não comprovam funcionamento da maquete.

## 11. Contratos implementados, sujeitos à revisão no PR

| Ponto | Proposta e justificativa |
|---|---|
| Operações iniciais | Cadastro, listagem e consulta, acompanhando o catálogo de máquinas e evitando definir edição de receitas antes das ordens |
| Etapas no cadastro | Exigir receita completa e gravar atomicamente, conforme a ADR-005 |
| Nome | 1 a 100 caracteres normalizados; duplicados permitidos, seguindo o padrão das máquinas |
| Ordem | Sequência explícita, única e consecutiva de 1 a N; array recebido pode estar fora de ordem |
| Duração | Segundos inteiros positivos, mantendo o exemplo existente e um contrato inicial simples |
| Identidade de etapa | Par produto/sequência, suficiente enquanto não há edição nem referências externas a etapas |
| Reuso de máquinas | Permitido em várias etapas; o catálogo não impõe passagem única |
| Máquina inexistente | `422` no cadastro, com lista de IDs ausentes para correção da receita |
| Listagem | Receita completa, ordenação determinística e sem paginação inicial |

Essas propostas não escolhem frontend, algoritmo de otimização, protocolo,
identificação física ou cloud. Edição/versionamento de receitas e sua relação
com o histórico de ordens deverão ser especificados antes dessas funcionalidades.
Mudanças arquiteturais relevantes decorrentes da revisão devem ser registradas
em ADR; esta proposta utiliza as ADRs já aceitas.
