# ADR-005 — SQLAlchemy, Pydantic e Alembic no backend

- Status: Aceita
- Data: 21/09/2026

## Contexto

O backend utilizará Python/FastAPI, SQLite e arquitetura em camadas,
conforme as ADRs 001 a 004. Precisamos definir como mapear entidades,
validar os contratos da API e reproduzir a evolução da estrutura do banco.

A equipe já possui experiência com SQLAlchemy e Pydantic. O domínio terá
relacionamentos entre máquinas, produtos, etapas e ordens de produção.
O cadastro de um produto e suas etapas deverá formar uma operação atômica.

## Decisão

- Utilizar SQLAlchemy 2.x como ORM, com acesso síncrono ao banco no MVP.
- Manter os models SQLAlchemy separados dos schemas Pydantic da API.
- Utilizar Alembic para criar e evoluir a estrutura do banco por migrations
  versionadas no repositório, desde a primeira tabela.
- Manter SQLite como banco inicial, conforme a ADR-002.

As versões exatas das dependências serão registradas na configuração do
backend durante sua implementação. Esta decisão não significa que os
componentes já estejam implementados.

## Responsabilidades e integração

- **Models SQLAlchemy:** tabelas, colunas, relacionamentos e restrições de persistência.
- **Schemas Pydantic:** contratos e validação dos dados de entrada e saída.
- **Repositories:** consultas e operações de persistência usando SQLAlchemy.
- **Services:** regras de negócio e coordenação da transação da operação completa.
- **Database:** engine, fábrica de sessões e suporte ao ciclo de vida das sessões.
- **Alembic:** histórico de alterações da estrutura do banco.

Cada requisição que acessar o banco terá uma sessão própria, encerrada ao
final. Não compartilhar uma sessão global entre requisições. Os services
coordenam commit/rollback da operação; repositories podem executar flush,
mas não devem confirmar transações independentemente. Assim, produto e
etapas poderão ser gravados juntos ou desfeitos juntos em caso de erro.

O acesso síncrono deverá ser integrado ao FastAPI por rotas/dependências
síncronas apropriadas, sem executar operações bloqueantes diretamente
em rotas assíncronas. O engine pode ser compartilhado; a sessão não.

## Migrations

Uma migration é um arquivo versionado que descreve uma alteração na
estrutura do banco. Por exemplo, a primeira criará `machines`; outra
poderá adicionar `products` e suas etapas posteriormente.

- Manter configuração em `backend/alembic.ini` e revisões em
  `backend/migrations/versions/`.
- API e Alembic devem usar a mesma configuração de banco.
- Configurar o Alembic com os metadados dos models SQLAlchemy.
- Aplicar revisões explicitamente com `alembic upgrade head`, a partir de
  `backend/`, após instalar dependências e configurar o ambiente.
- Não usar `create_all()` na inicialização da API como substituto das migrations.
- Revisar arquivos gerados por `--autogenerate` antes de aplicá-los e versioná-los.
- Depois de uma revisão ser integrada e utilizada pela equipe, realizar
  novas alterações em novas revisões, preservando o histórico anterior.
- Separar mudanças de estrutura de dados opcionais de demonstração.

Um `downgrade` pode remover tabelas ou dados; não equivale a restauração
de backup. Testes de reversão devem utilizar bancos descartáveis e o efeito
da reversão deve ser documentado em cada migration.

## Justificativa

A escolha aproveita ferramentas conhecidas pela equipe e preserva a
separação entre contratos HTTP e persistência da ADR-004. Alembic concretiza
o requisito de estrutura reproduzível da ADR-002 e permite que cada integrante
atualize seu banco a partir do mesmo histórico.

O acesso síncrono atende ao escopo inicial de baixa concorrência sem exigir
uma segunda abordagem para sessões e drivers assíncronos.

## Alternativas consideradas

- **SQL direto:** viável, mas exigiria mais mapeamento manual conforme o domínio crescer.
- **SQLModel:** não foi escolhido; manter SQLAlchemy e Pydantic separados
  aproveita a experiência existente e explicita as responsabilidades de cada modelo.
- **Scripts SQL manuais:** reproduzem a estrutura, mas exigem convenções próprias
  para acompanhar quais alterações já foram aplicadas.
- **Somente `create_all()`:** não fornece histórico de evolução das tabelas existentes.
- **SQLAlchemy assíncrono:** poderá ser reavaliado se requisitos de concorrência
  e medições indicarem necessidade; não é necessário para o MVP atual.

## Consequências

### Positivas

- Persistência organizada em models e repositories.
- Contratos da API independentes da representação do banco.
- Transações abrangendo toda a operação de negócio.
- Estrutura do banco reproduzível e alterações revisáveis em Pull Requests.

### Negativas

- Curva de aprendizado do Alembic e etapa explícita de atualização do banco.
- Necessidade de manter models, schemas e migrations coerentes.
- Migrations geradas automaticamente exigem revisão; não detectam toda intenção de mudança.
- Alterações de estrutura precisam considerar as limitações do SQLite.

## Critérios para reavaliação

Reavaliar o acesso síncrono, o banco ou as ferramentas se houver requisitos
novos de concorrência, múltiplas instâncias ou dificuldades concretas de manutenção.

## Referências

- [ADR-002 — SQLite](0002-sqlite.md).
- [ADR-004 — Arquitetura em camadas](0004-arquitetura-em-camadas-backend.md).
- [SQLAlchemy — ORM Quick Start](https://docs.sqlalchemy.org/en/20/orm/quickstart.html).
- [SQLAlchemy — Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).
- [Alembic — Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
- [Alembic — Autogenerate e suas limitações](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).
