# SPEC-0008 — Migração do SQLite para PostgreSQL

> **Status:** Implementada e validada localmente; execução da CI e revisão de
> outro integrante pendentes.
>
> **Data:** 09/11/2026
>
> **Implementação:** 10/11/2026, somente com o catálogo-base, conforme decisão
> do responsável.
>
> **Origem:** Evolução da arquitetura para permitir que backend e Grafana se
> conectem ao banco pela rede e para sustentar os experimentos de
> Telecomunicações do projeto.

## 1. Objetivo

Substituir o SQLite pelo PostgreSQL como único banco suportado pelo backend do
Axion, preservando o histórico Alembic, os dados existentes que forem selecionados
para migração e os contratos HTTP atuais.

A entrega deve disponibilizar um ambiente local reproduzível, executar a API e
as migrations por conexão TCP, validar o backend contra PostgreSQL real e deixar
uma fronteira segura para a futura integração do Grafana.

## 2. Dependência arquitetural

Esta spec implementa a ADR-009, aceita em 09/11/2026. A ADR-002 está substituída
e o backend suporta somente PostgreSQL desde 10/11/2026.

## 3. Escopo

### Incluído

- Serviço PostgreSQL em container para desenvolvimento e testes locais.
- Volume persistente, healthcheck e rede nomeada no ambiente de containers.
- Driver Psycopg 3 síncrono e URL SQLAlchemy `postgresql+psycopg`.
- Configuração única de conexão consumida pela API e pelo Alembic.
- Adaptação do engine para PostgreSQL, sem pragmas ou opções de SQLite.
- Execução do histórico Alembic existente, do `base` ao `head`, em banco vazio.
- Inicialização do PostgreSQL somente com o catálogo-base reproduzido pelo
  histórico Alembic, conforme decisão do responsável em 10/11/2026.
- Testes de API, services, repositories, constraints e migrations em PostgreSQL.
- Serviço PostgreSQL descartável no workflow de CI do backend.
- Documentação de instalação, execução, migração, backup, validação e rollback.
- Preparação do princípio de menor privilégio para uma futura fonte de dados do
  Grafana, sem implementar dashboards nesta entrega.

### Fora do escopo

- Dashboards, alertas, provisionamento ou container do Grafana.
- Novas tabelas de telemetria, rastreabilidade, execução física ou métricas.
- Protocolo entre Arduino/ESP32 e backend.
- Acesso direto de dispositivos embarcados ao banco.
- Containerização obrigatória do backend ou frontend.
- Deploy em cloud, alta disponibilidade, replicação ou recuperação contínua.
- Mudança para SQLAlchemy assíncrono.
- Alteração de contratos HTTP ou de regras de negócio existentes.
- Transferência das ordens e de outros registros do arquivo SQLite local.

## 4. Arquitetura da primeira entrega

```text
API FastAPI (host ou container)
        |
        | TCP + URL postgresql+psycopg
        v
PostgreSQL (container) <--- Grafana (integração futura, usuário somente leitura)

Arduino/ESP32 ---> API/protocolo futuro
Arduino/ESP32 -X-> PostgreSQL
```

No ambiente local padrão, o PostgreSQL poderá publicar a porta para o host apenas
em `127.0.0.1`. Serviços no mesmo Compose usarão o nome DNS do serviço na rede de
containers. Exposição à LAN não fará parte da configuração padrão.

## 5. Configuração

### 5.1 Variável da aplicação

Substituir `AXION_DATABASE_PATH` por `AXION_DATABASE_URL`. A variável deve conter
uma URL completa compatível com SQLAlchemy, por exemplo:

```text
postgresql+psycopg://axion_app:senha_local@127.0.0.1:5432/axion
```

O arquivo de exemplo usará valores locais não sensíveis. Senhas reais e arquivos
`.env` continuarão fora do Git. A aplicação deverá falhar com mensagem clara ao
receber uma URL ausente, malformada ou de dialeto não suportado; não haverá
fallback silencioso para um arquivo SQLite.

API e Alembic devem ler a mesma configuração. Se no futuro forem separados o
usuário de migration e o usuário de runtime, isso deverá ser feito sem duplicar a
origem da URL nem armazenar segredo no `alembic.ini`.

### 5.2 Engine e sessões

- Criar o engine a partir da URL PostgreSQL.
- Remover `check_same_thread`, listener de `PRAGMA foreign_keys` e tipos de
  conexão importados de `sqlite3`.
- Preservar uma sessão síncrona por requisição e `expire_on_commit=False`.
- Habilitar verificação de conexão antes de reutilizá-la (`pool_pre_ping`).
- Descartar o engine no encerramento da aplicação, como ocorre atualmente.
- Não criar tabelas durante o startup da API.

### 5.3 Container PostgreSQL

A definição do serviço deverá:

- fixar uma versão principal suportada do PostgreSQL, sem usar a tag `latest`;
- persistir dados em volume nomeado;
- possuir healthcheck com `pg_isready`;
- reiniciar somente conforme política explícita do ambiente;
- receber banco, usuário e senha por variáveis de ambiente;
- publicar a porta no loopback do host no perfil de desenvolvimento;
- não conter credenciais reais versionadas.

Remover o volume para recriar o banco é uma ação destrutiva e deverá ser indicada
somente para ambientes descartáveis.

## 6. Migrations e compatibilidade de schema

As quatro revisões Alembic atuais devem ser executadas sem alteração de seus IDs
e sem substituição por uma migration consolidada. Antes do corte, validar:

- criação de todas as tabelas, chaves primárias e estrangeiras;
- CHECKs de sequência, duração e quantidade positivas;
- catálogo inicial idempotente;
- preservação de dados nos upgrades e efeitos documentados dos downgrades;
- coerência entre metadata e banco por `alembic check`.

As revisões já integradas não devem ser reescritas. Se a validação revelar uma
incompatibilidade que impeça executar o histórico em PostgreSQL, a implementação
deve parar e a solução deve ser revista pela equipe antes de alterar o histórico.

PostgreSQL aplica chaves estrangeiras por padrão. Testes não devem procurar
`PRAGMA`; devem verificar o efeito das constraints por operações inválidas.

## 7. Migração de dados existentes

O responsável decidiu em 10/11/2026 iniciar somente com o catálogo-base. O
arquivo SQLite local continha três máquinas, três produtos, sete etapas e uma
ordem com três itens. Nenhum desses registros foi importado; máquinas, produtos
e etapas foram recriados pela migration `bb94b7e72eb7`, e o PostgreSQL iniciou
sem ordens.

O arquivo de origem permanece ignorado pelo Git e não foi apagado. Não foi criada
ferramenta de ETL nem caminho de compatibilidade com SQLite. Se algum registro
histórico precisar ser recuperado no futuro, a transferência deverá ser tratada
em tarefa própria, com backup, validação de referências e ajuste das sequências.

## 8. Usuários e permissões

Na primeira entrega, o usuário da aplicação poderá ser também o proprietário do
banco local para manter a operação simples. Essa concessão não deve ser reutilizada
pelo Grafana.

Na integração de observabilidade, criar `axion_grafana` (ou nome equivalente)
com login próprio e somente `SELECT` nas relações estritamente necessárias. O
usuário não poderá criar objetos, alterar dados nem executar migrations. Views
específicas serão preferidas quando as tabelas de execução e telemetria existirem.

## 9. Testes e integração contínua

### 9.1 Testes locais

Os testes do backend devem usar PostgreSQL real, nunca SQLite em memória como
substituto. Cada teste ou grupo destrutivo deverá receber banco descartável e
isolado para permitir upgrade, downgrade e alterações de catálogo sem interferência.

Cobertura mínima:

- inicialização da API com URL PostgreSQL válida;
- erro de configuração para URL ausente ou dialeto incorreto;
- contratos HTTP existentes sem alteração;
- commit e rollback das operações atômicas;
- constraints de chave estrangeira, chave composta e CHECK;
- histórico `base -> head`, repetição de upgrade, downgrade e novo upgrade;
- catálogo inicial em banco vazio e banco previamente populado;
- persistência observada por nova instância da aplicação;
- `alembic check` sem diferenças.

### 9.2 CI

O workflow do backend deverá iniciar um serviço PostgreSQL com healthcheck e
credenciais exclusivas de teste. A URL será fornecida pelo ambiente do job. O
job deve aguardar a saúde do serviço antes de executar migrations e testes.

A CI não deve depender de serviço externo, segredo de produção ou volume
persistente entre execuções.

## 10. Corte e rollback operacional

### Corte

1. confirmar que a ADR-009 e esta spec continuam aprovadas;
2. manter o arquivo SQLite antigo sem escrita e fora do Git;
3. subir PostgreSQL e aplicar migrations até `head`;
4. confirmar o catálogo-base e a ausência de ordens;
5. configurar API e Alembic com a URL PostgreSQL;
6. executar smoke tests de máquinas, produtos, ordens e planejamento;
7. liberar o backend.

### Rollback

Antes de dados relevantes serem gravados, o volume PostgreSQL pode ser recriado e
as migrations reaplicadas. Retornar ao SQLite exige restaurar uma versão anterior
do código, pois o backend atual não mantém compatibilidade com dois dialetos.
Depois de novas escritas no PostgreSQL, qualquer retorno exige interromper o
serviço e reconciliar os dados.

## 11. Critérios de aceite

- [x] ADR-009 aceita pelo responsável em 09/11/2026.
- [x] PostgreSQL sobe por comando documentado e atinge estado saudável.
- [x] API e Alembic conectam-se por TCP usando configuração de ambiente.
- [x] Nenhum caminho de execução depende de SQLite ou `PRAGMA`.
- [x] Histórico Alembic chega ao `head` em PostgreSQL vazio.
- [x] `alembic check` não encontra diferenças.
- [x] Todos os 258 testes do backend passam localmente contra PostgreSQL.
- [ ] Workflow atualizado aguarda execução no GitHub Actions.
- [x] Nenhum dado foi selecionado para transferência; catálogo-base recriado.
- [x] Sequências geram novos IDs sem colisão nos testes de integração.
- [x] Contratos HTTP atuais permanecem compatíveis.
- [x] Credenciais reais não estão no repositório nem nos logs.
- [x] Porta do banco não é exposta à LAN na configuração padrão.
- [x] README do backend e documentação arquitetural refletem o novo estado.
- [x] Validação descrita como software/rede; nenhuma validação em hardware é alegada.

## 12. Validação manual mínima

Com o PostgreSQL saudável e as migrations aplicadas:

1. iniciar a API;
2. consultar o catálogo base;
3. criar máquina, produto e ordem;
4. planejar a ordem;
5. reiniciar a API e confirmar a persistência;
6. tentar inserir referências e quantidades inválidas diretamente em banco de
   teste e confirmar rejeição.

Essa validação comprova integração de software por rede local. Não comprova
comunicação com Arduino/ESP32, segurança de uma rede externa, Grafana configurado
nem execução na maquete física.

## 13. Pendências posteriores

- ADR e spec do protocolo de comunicação com dispositivos.
- Modelo persistente de execução, telemetria e rastreabilidade.
- Views e usuário somente leitura para Grafana.
- Container/provisionamento do Grafana e dashboards.
- Política de backup periódico e recuperação para ambiente de demonstração.
- Decisão de cloud e, se necessária, criptografia TLS entre hosts.

## 14. Referências

- [ADR-009 — PostgreSQL como banco de dados em rede](../adr/0009-postgresql-banco-em-rede.md)
- [ADR-002 — SQLite como banco inicial](../adr/0002-sqlite.md)
- [ADR-005 — SQLAlchemy, Pydantic e Alembic](../adr/0005-sqlalchemy-pydantic-alembic.md)
- [Arquitetura do Axion](../architecture.md)
- [README do backend](../../backend/README.md)

