# SPEC-0004 — Criação de ordens de produção

> **Status:** Implementada e validada localmente e na CI; revisão de PR pendente
>
> **Data:** 03/10/2026
>
> **Implementação:** 13/10/2026, por solicitação do responsável.

## 1. Objetivo

Permitir criar e consultar ordens de produção compostas por produtos existentes
e suas respectivas quantidades.

Uma ordem registra a demanda solicitada. Seu cadastro não otimiza a produção,
não reserva máquinas, não cria unidades físicas e não inicia a execução na
maquete. O planejamento da produção será tratado em uma spec posterior, após
revisão do modelo de ordens. A solicitação do responsável autorizou esta
implementação; a revisão por outro integrante permanece necessária antes do merge.

## 2. Referências e contexto

- [Visão geral](../visao-geral.md): fluxo de produtos, ordens, otimização e
  execução física.
- [Arquitetura](../architecture.md): organização do backend e tecnologias
  aceitas.
- [SPEC-0001](0001-backend-machines.md): cadastro de máquinas e padrões de API.
- [SPEC-0002](0002-ci-testes-automatizados.md): execução de testes do backend
  na CI.
- [SPEC-0003](0003-backend-products.md): cadastro de produtos e receitas
  produtivas.
- [ADR-001](../adr/0001-python-fastapi.md): Python e FastAPI.
- [ADR-002](../adr/0002-sqlite.md): SQLite.
- [ADR-003](../adr/0003-monorepo.md): monorepo.
- [ADR-004](../adr/0004-arquitetura-em-camadas-backend.md): responsabilidades
  das camadas do backend.
- [ADR-005](../adr/0005-sqlalchemy-pydantic-alembic.md): SQLAlchemy, schemas
  Pydantic separados e migrations Alembic.
- [README do backend](../../backend/README.md): instalação, migrations e
  validação locais.

O backend já permite consultar produtos com suas receitas. A SPEC-0003 não
incluiu ordens nem quantidades. Esta spec propõe a primeira operação que reúne
esses produtos em uma demanda persistida; algoritmo de otimização e execução
continuam fora do escopo.

## 3. Escopo

### Incluído

- Criar uma ordem com um ou mais produtos existentes e suas quantidades.
- Listar ordens e consultar uma ordem por ID, incluindo seus itens.
- Validar a estrutura da entrada, quantidades e referências aos produtos.
- Persistir a ordem e todos os seus itens na mesma transação.
- Criar models SQLAlchemy, schemas Pydantic, repositories e services conforme
  a arquitetura existente.
- Criar migration Alembic para as tabelas da ordem e seus itens.
- Cobrir as regras, a API, a persistência, as migrations e a inicialização das
  rotas com testes automatizados.
- Atualizar a documentação do backend com os comandos e contratos novos.

### Fora desta entrega

- Editar, excluir, cancelar, iniciar ou finalizar ordens.
- Alterar, versionar ou excluir produtos e suas receitas.
- Gerar programação, calcular duração estimada ou otimizar a utilização das
  máquinas.
- Reservar máquinas ou coordenar ordens simultâneas.
- Criar unidades físicas, identificadores individuais ou histórico de etapas.
- Atualizar estado operacional, comunicar-se com firmware ou controlar a maquete.
- Autenticação, autorização, frontend, Grafana e deploy.

Uma ordem criada nesta entrega representa somente uma demanda registrada no
banco. Sua criação não deve ser descrita ao usuário como produção iniciada ou
como programação validada.

## 4. Conceito das entidades

Uma `ProductionOrder` representa uma solicitação de produção. Sua identidade é
um ID gerado pelo banco. Uma `ProductionOrderItem` associa um produto à
quantidade solicitada dentro da ordem.

### Ordem de produção

| Campo | Tipo | Origem | Descrição |
|---|---|---|---|
| `id` | Inteiro positivo | Backend/banco | Identificador único e estável |
| `items` | Lista de itens | Cadastro | Produtos e quantidades solicitadas; deve conter ao menos um item |

### Item da ordem

| Campo | Tipo | Origem | Descrição |
|---|---|---|---|
| `product_id` | Inteiro positivo | Cadastro | Referência a um produto existente |
| `quantity` | Inteiro positivo | Cadastro | Número de unidades solicitadas daquele produto |

A identidade de um item é o par `(order_id, product_id)`. Cada produto pode
aparecer no máximo uma vez na mesma ordem; a quantidade deve ser informada em
um único item. A ordem de entrada dos itens não representa prioridade nem
sequência de fabricação.

Esta implementação não adiciona status ou horário de criação: nenhum fluxo de
execução ou regra que dependa desses campos foi definido nas specs anteriores.
Também não copia a receita para a ordem. Como a SPEC-0003 não oferece edição ou
exclusão de produtos, o item referencia o produto cadastrado; caso edição ou
exclusão de receitas seja aprovada futuramente, será necessário definir como
preservar a interpretação histórica das ordens existentes.

## 5. Regras

| Código | Regra |
|---|---|
| RN-01 | O corpo deve conter `items`, uma lista não vazia de itens. |
| RN-02 | Cada item deve conter somente `product_id` e `quantity`; campos ausentes, nulos ou extras são rejeitados, inclusive `id`, `order_id` e `unit_id`. |
| RN-03 | `product_id` e `quantity` devem ser inteiros JSON positivos. Rejeitar booleanos, strings numéricas e números decimais, inclusive `1.0`, sem coerção. |
| RN-04 | Um mesmo `product_id` não pode aparecer mais de uma vez na ordem. Rejeitar duplicatas em vez de somar ou escolher uma quantidade implicitamente. |
| RN-05 | Todos os produtos referenciados devem existir. Se houver referências ausentes, rejeitar a ordem inteira e informar todos os IDs ausentes, sem repetição e em ordem crescente. |
| RN-06 | Não criar, alterar ou remover produtos implicitamente durante a criação da ordem. |
| RN-07 | A ordem e todos os seus itens devem ser persistidos na mesma transação. Só retornar sucesso após commit; falhas devem desfazer toda a gravação. |
| RN-08 | O ID da ordem é gerado pelo banco e não pode ser informado no cadastro. |
| RN-09 | A criação de uma ordem não cria unidades físicas nem registros de execução. |
| RN-10 | Uma consulta por ID positivo inexistente retorna recurso não encontrado. |

Validar primeiro a estrutura e os tipos; depois verificar IDs de produto
duplicados; por último consultar a existência dos produtos. Não é necessário
agrupar erros de fases diferentes na mesma resposta.

## 6. Contrato HTTP

Manter o padrão de rotas sem prefixo de versão utilizado para máquinas e
produtos.

| Método e rota | Resultado | Erros previstos |
|---|---|---|
| `POST /orders` | `201 Created`, com a ordem e seus itens | `422` para entrada inválida, produtos repetidos ou produtos inexistentes |
| `GET /orders` | `200 OK`, array de ordens completas | — |
| `GET /orders/{order_id}` | `200 OK`, ordem com seus itens | `404` para ID inexistente; `422` para ID inválido |

### 6.1. Criar ordem

Requisição para `POST /orders`:

```json
{
  "items": [
    { "product_id": 1, "quantity": 3 },
    { "product_id": 2, "quantity": 2 }
  ]
}
```

Resposta `201 Created`:

```json
{
  "id": 1,
  "items": [
    { "product_id": 1, "quantity": 3 },
    { "product_id": 2, "quantity": 2 }
  ]
}
```

IDs são ilustrativos; clientes devem usar IDs retornados pela API e não
presumir que sejam consecutivos. Antes de criar a ordem, os produtos devem
existir no catálogo. A resposta contém os itens em ordem crescente de
`product_id`, independentemente da ordem recebida. Cada POST válido cria uma
ordem com ID próprio, inclusive se o conteúdo for igual ao de outra ordem.

### 6.2. Listar e consultar ordens

`GET /orders` retorna um array no formato dos objetos de criação, em ordem
crescente de ID da ordem. Os itens de cada ordem são retornados em ordem
crescente de `product_id`. Sem ordens, retorna `200 OK` com `[]`. Paginação,
filtros e busca ficam fora desta entrega.

`GET /orders/{order_id}` retorna o mesmo formato usado na criação. O parâmetro
de caminho deve representar um inteiro positivo. Um ID positivo inexistente
retorna `404 Not Found`:

```json
{ "detail": "Ordem de produção não encontrada." }
```

### 6.3. Erros de validação e infraestrutura

- Erros de estrutura, tipos, campos extras ou valores inválidos retornam `422`
  na estrutura de validação FastAPI/Pydantic, com `detail` contendo os erros e
  a localização do campo. Não fixar o texto interno das mensagens da biblioteca.
- Produto repetido retorna `422` com:

```json
{ "detail": "Cada produto pode aparecer somente uma vez na ordem." }
```

- Produtos inexistentes retornam `422`; listar todos os IDs ausentes, sem
  duplicatas e em ordem crescente:

```json
{
  "detail": "Um ou mais produtos da ordem não existem.",
  "product_ids": [9, 12]
}
```

- Falhas inesperadas de persistência devem causar rollback e retornar erro de
  servidor genérico, com detalhes somente no log. Não expor SQL, caminhos
  internos ou stack traces e não converter falhas de banco em `404` ou `422`.

## 7. Organização

Arquivos propostos para a estrutura existente:

```text
backend/
├── app/
│   ├── controllers/order_controller.py
│   ├── services/order_service.py
│   ├── repositories/order_repository.py
│   ├── models/production_order.py
│   └── schemas/order_schema.py
├── migrations/versions/<revision>_create_production_orders.py
└── tests/
    ├── test_order_service.py
    ├── test_order_api.py
    └── test_migrations.py
```

- Controller: receber requisições, chamar o service e mapear erros de domínio
  para respostas HTTP; não consultar o banco diretamente.
- Service: revalidar as regras de negócio, verificar os produtos referenciados
  e coordenar a transação da ordem e de todos os itens.
- Repositories: consultar produtos e persistir/carregar ordens usando a sessão
  da operação; não realizar commits independentes.
- Models: representar a ordem, seus itens, relacionamentos e restrições de
  persistência.
- Schemas: separar entrada e saída da API dos models SQLAlchemy.
- Integração: registrar as rotas no `main.py` e carregar os models nos
  metadados utilizados pelo Alembic.

Reutilizar configuração, base declarativa, sessões síncronas e fixtures de
teste existentes. Estender o repository de produtos para consultar em lote os
IDs necessários, se isso simplificar a validação. Não criar infraestrutura de
banco paralela nem abstrações genéricas sem necessidade concreta.

## 8. Persistência e ambiente

Criar uma nova revisão Alembic após o head vigente no momento da implementação,
sem alterar migrations já integradas. A migration deve criar:

| Tabela | Colunas e restrições propostas |
|---|---|
| `production_orders` | `id` inteiro, chave primária gerada pelo banco |
| `production_order_items` | `order_id`, `product_id` e `quantity` inteiros obrigatórios; chave primária composta por `(order_id, product_id)` |

- `production_order_items.order_id` referencia `production_orders.id`;
  `product_id` referencia `products.id`.
- Definir CHECK para `quantity > 0`; a exigência de ao menos um item é validada
  pelo service antes da persistência.
- Não permitir que a exclusão de um produto referenciado invalide uma ordem.
  Não adicionar endpoint de exclusão nesta entrega.
- Ordem e itens devem ser escritos atomicamente. Repositories podem fazer
  `flush`, mas somente o service controla commit/rollback, conforme a ADR-005.
- API e Alembic usam `AXION_DATABASE_PATH` e as migrations são aplicadas
  explicitamente por `alembic upgrade head`. Não usar `create_all()` na
  inicialização da API.
- O downgrade remove primeiro `production_order_items` e depois
  `production_orders`. Testar reversão somente em banco descartável; ela remove
  as ordens persistidas.

## 9. Critérios de aceite

Marcar os itens somente após implementação e validação. As evidências locais
estão na seção 10; o merge exige CI e revisão de outro integrante.

- [x] CA-01: OpenAPI apresenta `POST /orders`, `GET /orders` e
  `GET /orders/{order_id}` com schemas e respostas previstos.
- [x] CA-02: Uma ordem válida com um ou mais produtos existentes retorna `201`,
  ID positivo e todos os itens com suas quantidades.
- [x] CA-03: Repetir a mesma demanda cria ordens com IDs distintos.
- [x] CA-04: Corpo ausente, `items` ausente, nulo, vazio ou de tipo incorreto,
  itens que não são objetos e campos ausentes, extras ou nulos retornam `422`.
- [x] CA-05: `product_id` e `quantity` rejeitam zero, negativos, booleanos,
  strings e decimais, inclusive `1.0`, sem gravar ordem ou itens.
- [x] CA-06: Produto repetido na mesma ordem retorna o erro definido e não
  persiste registros.
- [x] CA-07: Produtos inexistentes retornam `422` com todos os IDs ausentes,
  ordenados e sem duplicatas; nenhuma parte da ordem é persistida.
- [x] CA-08: Listagem vazia retorna `[]`; ordens são listadas por ID e itens
  por `product_id`, sem perda ou duplicação.
- [x] CA-09: Consultar ID positivo inexistente retorna `404`; IDs inválidos
  retornam `422`.
- [x] CA-10: Falhas durante gravação ou commit fazem rollback da ordem e de
  todos os itens, sem expor detalhes internos na resposta.
- [x] CA-11: Migrations upgrade/downgrade funcionam em banco descartável,
  preservando produtos e receitas no upgrade.
- [x] CA-12: A suíte completa do backend passa localmente e na CI.
- [x] CA-13: README do backend documenta criação e consulta de ordens, erros,
  migrations e comandos de validação.

## 10. Implementação e validação

Implementados `POST /orders`, `GET /orders` e `GET /orders/{order_id}`, com
models, schemas, repository e service separados. A revisão Alembic
`f47c9a2e8106` sucede `bb94b7e72eb7`, cria ordens e itens e preserva o catálogo.
Nenhuma revisão previamente integrada foi alterada.

Os testes em `test_order_api.py`, `test_order_service.py`, `test_migrations.py`
e `test_main.py` cobrem contratos, regras fora de HTTP, persistência, rollback,
restrições SQLite, migrations e carregamento das rotas sem iniciar o servidor.
A validação utiliza bancos temporários e falhas simuladas, sem hardware real.

Comandos locais em `backend/`: `uv run --locked pytest -q`,
`uv run --locked ruff check .` e `uv run --locked ruff format --check .`.
O teste de migrations executa também `alembic check` em banco descartável.
Validação local: 203 testes passaram; Ruff (lint e formatação) passou.
A CI aprovou o commit de implementação `6e9a6c4` no check `Tests (Python 3.12)`
([execução](https://github.com/thiago-fischer/unifecaf-expotech-axion/actions/runs/38476809424)).
O [PR #7](https://github.com/thiago-fischer/unifecaf-expotech-axion/pull/7)
aguarda revisão por outro integrante antes do merge.
