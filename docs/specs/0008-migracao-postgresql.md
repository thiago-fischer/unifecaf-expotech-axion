# SPEC-0008 — Migração do SQLite para PostgreSQL

> **Status:** Aprovada para implementação; implementação ainda não iniciada.
>
> **Data:** 09/11/2026
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

Esta spec implementa a ADR-009, aceita em 09/11/2026. A ADR-002 está substituída,
mas SQLite continua sendo o banco executado pelo código atual até a conclusão
desta spec. PostgreSQL não deve ser apresentado como implementado antes que os
critérios de aceite técnicos sejam atendidos.

## 3. Escopo

### Incluído

- Serviço PostgreSQL em container para desenvolvimento e testes locais.
- Volume persistente, healthcheck e rede nomeada no ambiente de containers.
- Driver Psycopg 3 síncrono e URL SQLAlchemy `postgresql+psycopg`.
- Configuração única de conexão consumida pela API e pelo Alembic.
- Adaptação do engine para PostgreSQL, sem pragmas ou opções de SQLite.
- Execução do histórico Alembic existente, do `base` ao `head`, em banco vazio.
- Processo controlado para copiar os registros atuais de SQLite quando houver
  dados que precisem ser preservados.
- Ajuste das sequências PostgreSQL depois da importação de IDs explícitos.
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

Antes da implementação, a equipe deve identificar quais arquivos SQLite contêm
dados que precisam ser preservados. Bancos apenas descartáveis podem ser
recriados pelo Alembic e pela migration do catálogo inicial.

Para cada banco preservado, o procedimento deverá:

1. interromper escritas e fazer uma cópia de segurança do arquivo SQLite;
2. criar um banco PostgreSQL vazio e aplicar o Alembic até a revisão
   `d8e063d489f1`, que contém o schema de máquinas, produtos e etapas, mas ainda
   não executa a migration do catálogo base;
3. copiar `machines`, `products` e `product_steps`, nessa ordem, mantendo IDs;
4. aplicar o restante do histórico até `head`; a revisão `bb94b7e72eb7` deverá
   reutilizar receitas base equivalentes e criar somente as que estiverem
   ausentes, e a revisão `f47c9a2e8106` criará as tabelas de ordens;
5. copiar `production_orders` e `production_order_items`, nessa ordem, mantendo
   IDs e referências;
6. ajustar as sequências de `machines`, `products` e `production_orders` para o
   maior ID presente depois da importação e dos dados base;
7. validar contagens, referências, constraints e amostras funcionais;
8. registrar origem, destino, horário e resultado, sem registrar credenciais.

A ferramenta de transferência deve abortar diante de conflito ou dado inválido,
marcar o destino como impróprio para corte e não alterar o arquivo SQLite de
origem. Como o procedimento atravessa revisões de schema, não deve prometer
rollback atômico de todas as fases: em caso de falha, o banco PostgreSQL de
destino será descartado e recriado. A ferramenta deve recusar um destino que não
esteja vazio ou exatamente no estado esperado, evitando duplicações na reexecução.

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
- transferência de dados e atualização das sequências;
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
2. criar backup verificável do SQLite selecionado;
3. subir PostgreSQL e aplicar migrations;
4. congelar escritas no SQLite;
5. transferir e validar os dados;
6. configurar API e Alembic com a URL PostgreSQL;
7. executar smoke tests de máquinas, produtos, ordens e planejamento;
8. liberar o backend e manter o backup SQLite sem escrita pelo período acordado.

### Rollback

Antes de novas escritas no PostgreSQL, o rollback pode restaurar a configuração
anterior e reabrir a cópia SQLite. Depois que o PostgreSQL receber novas escritas,
o retorno não é automático: será necessário interromper o serviço e reconciliar
os dados. Essa limitação deve constar do checklist de corte.

## 11. Critérios de aceite

- [x] ADR-009 aceita pelo responsável em 09/11/2026.
- [ ] PostgreSQL sobe por comando documentado e atinge estado saudável.
- [ ] API e Alembic conectam-se por TCP usando configuração de ambiente.
- [ ] Nenhum caminho de execução depende de SQLite ou `PRAGMA`.
- [ ] Histórico Alembic chega ao `head` em PostgreSQL vazio.
- [ ] `alembic check` não encontra diferenças.
- [ ] Todos os testes do backend passam contra PostgreSQL no ambiente local e CI.
- [ ] Dados selecionados são migrados sem perda, duplicação ou quebra de referência.
- [ ] Próximos IDs gerados não colidem com IDs importados.
- [ ] Contratos HTTP atuais permanecem compatíveis.
- [ ] Credenciais reais não estão no repositório nem nos logs.
- [ ] Porta do banco não é exposta à LAN na configuração padrão.
- [ ] README do backend e documentação arquitetural refletem o novo estado.
- [ ] Validação descrita como software/rede; nenhuma validação em hardware é alegada.

## 12. Validação manual mínima

Com o PostgreSQL saudável e as migrations aplicadas:

1. iniciar a API;
2. consultar o catálogo base;
3. criar máquina, produto e ordem;
4. planejar a ordem;
5. reiniciar a API e confirmar a persistência;
6. tentar inserir referências e quantidades inválidas diretamente em banco de
   teste e confirmar rejeição;
7. conectar com um usuário somente leitura de prova e confirmar que `SELECT`
   funciona e `INSERT` é negado.

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

