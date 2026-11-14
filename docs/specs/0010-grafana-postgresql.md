# SPEC-0010 — Grafana com PostgreSQL

> **Status:** Aceita para implementação pelo responsável do projeto em
> 14/11/2026. Implementação e validação pendentes.
>
> **Data:** 14/11/2026
>
> **Origem:** Primeira entrega de observabilidade prevista na arquitetura do
> Axion e preparada pela migração para PostgreSQL da SPEC-0008.

## 1. Objetivo

Adicionar o Grafana ao ambiente local do Axion como serviço independente em
container, conectado ao PostgreSQL por uma credencial exclusiva e somente de
leitura.

A entrega deve disponibilizar um ambiente reproduzível, provisionar a fonte de
dados e um dashboard inicial sem configuração manual, e apresentar apenas
informações que já estejam persistidas pelo backend. Esta spec não transforma
o estado em memória do controlador nem da execução simulada em telemetria
persistida.

## 2. Dependência arquitetural

Esta spec implementa a integração de observabilidade já autorizada pela
[ADR-009](../adr/0009-postgresql-banco-em-rede.md), que estabelece:

- PostgreSQL como banco relacional em rede do Axion;
- backend como único componente autorizado a alterar dados de domínio;
- Grafana com conexão própria e somente de leitura;
- dispositivos embarcados sem acesso direto ao banco;
- ausência de exposição do PostgreSQL à rede local por padrão.

Não é necessária uma nova ADR para esta primeira entrega. A introdução de um
modelo de telemetria, outro armazenamento de métricas, TimescaleDB, Prometheus,
alertas ou observabilidade distribuída exigirá nova análise arquitetural.

## 3. Estado atual e fontes disponíveis

O banco possui as seguintes relações de domínio disponíveis para consulta:

- `machines`;
- `products`;
- `product_steps`;
- `production_orders`;
- `production_order_items`.

O planejamento da produção é transitório e não é persistido. O estado do
controlador, a posição das peças, os comandos, a execução simulada, as leituras
RFID e os resultados de QA permanecem em memória. Portanto, esses dados não
estarão disponíveis no dashboard desta entrega.

As tabelas atuais também não possuem dimensão temporal de criação ou execução.
O dashboard inicial não apresentará séries históricas artificiais nem usará IDs
como substitutos de tempo.

## 4. Escopo

### 4.1 Incluído

- Serviço Grafana em container no Compose da raiz.
- Imagem oficial OSS `grafana/grafana:13.3.1`, fixada em versão de patch.
- Porta `3000` publicada somente em `127.0.0.1`, configurável por variável de
  ambiente.
- Volume nomeado e separado para o estado interno do Grafana.
- Healthcheck do serviço pela API de saúde do Grafana.
- Participação do Grafana na rede Docker `axion`.
- Fonte de dados PostgreSQL provisionada por arquivo YAML versionado.
- Dashboard inicial provisionado por arquivo versionado.
- Credencial PostgreSQL exclusiva para o Grafana, com menor privilégio.
- Preparação idempotente da role de leitura para volumes PostgreSQL novos e já
  existentes.
- Configuração administrativa do Grafana por variáveis de ambiente.
- Arquivos de exemplo sem senhas reais.
- Documentação de instalação, execução, acesso, validação e recuperação.
- Validações automatizadas ou scripts reproduzíveis para configuração,
  conectividade e permissões quando houver suporte no módulo.

### 4.2 Fora do escopo

- Tabelas novas de telemetria, métricas, auditoria ou execução.
- Persistência do planejamento ou da execução simulada.
- Captura de pacotes com Wireshark, TShark ou Dumpcap.
- Métricas de rede, latência, retransmissões ou códigos HTTP.
- Estado ao vivo da maquete virtual ou física.
- Métricas de hardware, Arduino ou ESP32.
- Prometheus, Loki, Tempo, OpenTelemetry ou TimescaleDB.
- Alertas, envio de e-mails e canais de notificação.
- SSO, LDAP ou integração com provedor externo de identidade.
- Incorporação de dashboards em `iframe` no frontend.
- Acesso anônimo ao Grafana.
- Exposição do Grafana, PostgreSQL ou demais serviços à LAN.
- Cloud, alta disponibilidade, replicação e backup remoto.
- Definição final dos indicadores da ExpoTech.

## 5. Arquitetura da entrega

```text
Navegador
    |
    | HTTP em 127.0.0.1:3000
    v
Grafana (container)
    |
    | PostgreSQL/TCP, usuário somente leitura
    v
PostgreSQL 17 (container)
    ^
    | SQLAlchemy + Psycopg 3, usuário da aplicação
    |
Backend FastAPI

Controlador/ESP32 --------> Backend/protocolo próprio
Controlador/ESP32 ----X---> PostgreSQL
```

O Grafana consultará o serviço `database:5432` pelo DNS da rede Docker. A
publicação local da porta do PostgreSQL continuará independente dessa conexão e
restrita a `127.0.0.1`.

O volume do Grafana armazenará somente seu estado interno, como usuários e
preferências. Dados de domínio do Axion continuarão exclusivamente no
PostgreSQL. O datasource e o dashboard necessários para reproduzir a entrega
serão provisionados a partir de arquivos versionados, não dependerão do estado
manual do volume.

## 6. Organização prevista

Antes da implementação, a estrutura existente deverá ser conferida. A entrega
deverá seguir, quando compatível, a organização:

```text
infrastructure/
└── grafana/
    ├── provisioning/
    │   ├── dashboards/
    │   │   └── dashboards.yaml
    │   └── datasources/
    │       └── postgresql.yaml
    └── dashboards/
        └── dados-persistidos.json
```

Um script ou job de preparação da role PostgreSQL poderá ficar em diretório de
infraestrutura específico. Ele não deverá ser colocado em
`docker-entrypoint-initdb.d` como único mecanismo de adoção, pois esse diretório
é executado apenas na primeira inicialização de um volume PostgreSQL vazio e não
atende aos volumes já existentes.

## 7. Container e execução

O serviço deverá:

- usar a imagem `grafana/grafana:13.3.1`;
- possuir o nome lógico `grafana` no Compose;
- publicar `127.0.0.1:${GRAFANA_PORT:-3000}:3000`;
- persistir `/var/lib/grafana` em volume nomeado próprio;
- montar os arquivos de provisioning e dashboards como somente leitura;
- aguardar o PostgreSQL saudável, as migrations concluídas e a preparação da
  role de leitura antes de iniciar;
- reiniciar sem exigir configuração manual do datasource ou dashboard;
- não instalar plugins externos nesta primeira entrega.

Atualizações de versão deverão ocorrer por alteração explícita e revisada da
tag. Não será utilizada a tag `latest`.

O healthcheck deverá consultar a API de saúde do Grafana dentro do container e
considerar o serviço saudável somente após resposta válida.

## 8. Configuração

### 8.1 Variáveis previstas

O arquivo `.env.example` da raiz deverá documentar valores locais não sensíveis
para, no mínimo:

```text
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=grafana_admin_local
GRAFANA_DB_USER=grafana_reader
GRAFANA_DB_PASSWORD=grafana_reader_local
```

Os nomes poderão ser ajustados durante a implementação para preservar o padrão
do Compose. Senhas reais e arquivos `.env` continuarão fora do Git.

O cadastro público de usuários deverá permanecer desabilitado. A configuração
local não habilitará acesso anônimo.

### 8.2 Datasource provisionado

A fonte de dados deverá ser declarada por YAML com as seguintes propriedades:

- nome estável: `Axion PostgreSQL`;
- tipo: `postgres`;
- endereço: `database:5432`;
- banco: valor de `POSTGRES_DB`;
- usuário e senha obtidos de variáveis de ambiente;
- versão PostgreSQL compatível com PostgreSQL 17;
- `sslmode: disable` somente para a rede Docker local desta entrega;
- limites conservadores de conexões abertas e ociosas;
- datasource padrão para os dashboards do Axion;
- edição manual desabilitada quando suportada pelo provisionamento.

O uso de `sslmode: disable` não aprova comunicação sem TLS fora do ambiente
local. Uma implantação externa deverá reavaliar certificados, hostname e
proteção da rede.

## 9. Usuário PostgreSQL e permissões

O Grafana não reutilizará `POSTGRES_USER`, a credencial do backend ou uma role
proprietária das tabelas.

A preparação da role deverá ser explícita, idempotente e compatível com volumes
existentes. Ela deverá:

1. criar a role `GRAFANA_DB_USER` quando ausente;
2. atualizar sua senha a partir do ambiente sem registrá-la nos logs;
3. conceder `CONNECT` somente ao banco necessário;
4. conceder `USAGE` no schema que contém as relações autorizadas;
5. conceder `SELECT` somente nas tabelas ou views aprovadas;
6. configurar privilégios padrão de leitura para novas relações criadas pelo
   proprietário usado pelo Alembic, quando aplicável;
7. não conceder criação de schema ou tabela;
8. não conceder `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES` ou
   `TRIGGER` nas relações de domínio;
9. não tornar a role superusuária, proprietária, replicadora ou capaz de criar
   bancos e outras roles.

O backend continuará como único caminho para mutações de negócio. O Grafana
será consumidor de leitura e não implementará regras de domínio.

## 10. Dashboard inicial

O dashboard provisionado terá o título **Axion — Dados persistidos** e deverá
deixar explícito que os dados representam cadastros e ordens armazenadas, não a
execução física em tempo real.

### 10.1 Painéis obrigatórios

1. **Máquinas cadastradas** — total de registros em `machines`.
2. **Produtos cadastrados** — total de registros em `products`.
3. **Ordens cadastradas** — total de registros em `production_orders`.
4. **Unidades solicitadas** — soma de `production_order_items.quantity`.
5. **Unidades solicitadas por produto** — agregação por produto, considerando
   todas as ordens persistidas.
6. **Composição das ordens** — tabela com ordem, produto e quantidade.
7. **Receitas dos produtos** — tabela com produto, sequência, máquina e tempo de
   processamento.
8. **Carga teórica cadastrada por máquina** — soma de quantidade multiplicada
   pelo tempo da etapa para as ordens persistidas.

### 10.2 Regras de apresentação

- IDs não serão apresentados como eixo temporal.
- A carga teórica não será denominada utilização real, produtividade ou tempo
  executado.
- O dashboard não afirmará que uma ordem foi iniciada ou concluída, pois esse
  estado não está persistido.
- Ausência de registros deverá produzir estado vazio compreensível, sem erro de
  consulta.
- Consultas deverão nomear colunas e unidades de forma legível em português.
- SQL dos painéis não deverá conter mutações nem dados sensíveis.

Views de leitura poderão ser propostas durante a implementação se reduzirem
duplicação ou melhorarem a clareza das consultas. Sua criação exigirá migration
Alembic versionada e revisão específica; não é obrigatória nesta entrega.

## 11. Segurança

- O Grafana será acessível somente pelo host local na configuração padrão.
- Credenciais administrativas e do datasource serão fornecidas por ambiente.
- Arquivos de provisioning não conterão senhas literais reais.
- Logs e mensagens de erro não deverão imprimir URLs contendo credenciais.
- O usuário do datasource terá somente leitura.
- Cadastro público e acesso anônimo permanecerão desabilitados.
- Plugins externos não serão instalados nesta entrega.
- O PostgreSQL não será exposto à LAN para atender ao Grafana.
- O dashboard não exibirá senhas, tokens, URLs com credenciais ou dados que não
  façam parte do escopo aprovado.

O provisioning do Grafana permite que consultas sejam editadas por quem possua
permissão administrativa no Grafana; por isso, a restrição efetiva contra
mutações deverá existir no PostgreSQL, não apenas na interface.

## 12. Testes e validação

### 12.1 Validações automatizadas ou reproduzíveis

A implementação deverá fornecer verificações para:

- validade do arquivo Compose após inclusão dos serviços;
- inicialização do PostgreSQL, migrations, preparação da role e Grafana;
- resposta saudável da API do Grafana;
- datasource provisionado e conectado;
- dashboard provisionado sem configuração manual;
- consultas `SELECT` permitidas para a role do Grafana;
- tentativas de mutação nas tabelas de domínio rejeitadas para essa role;
- provisioning funcional com banco vazio e com catálogo-base;
- reinício do Grafana sem perda da configuração reproduzível;
- ausência de credenciais reais nos arquivos versionados.

Testes que dependam do container deverão ser identificados como integração e
documentar seus pré-requisitos.

### 12.2 Validação manual mínima

1. Copiar o arquivo de ambiente de exemplo e iniciar o Compose conforme o
   README da raiz.
2. Confirmar PostgreSQL e Grafana saudáveis em `docker compose ps`.
3. Abrir `http://127.0.0.1:3000` e autenticar com a credencial local definida.
4. Confirmar que `Axion PostgreSQL` está provisionado e responde ao teste de
   conexão.
5. Abrir `Axion — Dados persistidos` sem criar painéis manualmente.
6. Comparar totais do dashboard com consultas SQL de referência.
7. Inserir uma ordem pela API e confirmar que os painéis de dados persistidos
   refletem a alteração após atualização.
8. Demonstrar, com a role do Grafana, que `SELECT` funciona e uma tentativa de
   `INSERT`, `UPDATE` ou `DELETE` em relação de domínio é rejeitada.
9. Reiniciar o serviço Grafana e confirmar que datasource e dashboard voltam
   provisionados.

Essa validação é de software e rede local. Ela não valida hardware, maquete
física, comunicação sem fio nem observabilidade da execução real.

## 13. Critérios de aceite

- [ ] Serviço Grafana usa `grafana/grafana:13.3.1`, sem tag `latest`.
- [ ] Grafana sobe pelo Compose e atinge estado saudável.
- [ ] Porta do Grafana é publicada somente em `127.0.0.1` por padrão.
- [ ] Estado interno do Grafana usa volume nomeado próprio.
- [ ] Datasource PostgreSQL é provisionado automaticamente.
- [ ] Dashboard `Axion — Dados persistidos` é provisionado automaticamente.
- [ ] Role exclusiva do Grafana é criada ou atualizada de forma idempotente.
- [ ] Role do Grafana consegue executar os `SELECT` necessários.
- [ ] Role do Grafana não consegue alterar relações de domínio.
- [ ] Backend permanece o único caminho para mutações de negócio.
- [ ] Dashboard não apresenta estado em memória como dado persistido.
- [ ] Painéis obrigatórios funcionam com catálogo-base e com banco sem ordens.
- [ ] Credenciais reais não são versionadas nem exibidas em logs.
- [ ] Cadastro público e acesso anônimo permanecem desabilitados.
- [ ] PostgreSQL e Grafana não são expostos à LAN na configuração padrão.
- [ ] Comandos de instalação, execução e validação estão documentados.
- [ ] Testes e validações executados são registrados sem alegar hardware real.

Os itens permanecem desmarcados porque esta spec está aceita, mas ainda não foi
implementada.

## 14. Rollback

Se a integração impedir a execução normal do ambiente local, o rollback deverá:

1. remover o serviço Grafana e o job de preparação da role do Compose;
2. remover mounts e variáveis exclusivos da integração;
3. preservar o backend, PostgreSQL, migrations e dados de domínio;
4. revogar os privilégios e remover a role de leitura somente após confirmar que
   não há outro consumidor autorizado;
5. remover o volume do Grafana apenas mediante ação explícita, pois essa operação
   apaga usuários e preferências locais do Grafana.

O rollback do Grafana não exige downgrade de migrations enquanto esta entrega
não criar views ou outras relações no banco.

## 15. Pendências posteriores

- persistência do histórico de execução e rastreabilidade;
- definição das métricas finais da ExpoTech;
- dashboards da maquete e das ordens executadas;
- integração de métricas de rede produzidas por TShark ou outra ferramenta;
- alertas e notificações;
- TLS para conexões fora do ambiente local;
- autenticação corporativa e controle de acesso por equipe;
- implantação em cloud;
- avaliação de Prometheus, Loki, Tempo ou OpenTelemetry quando houver dados e
  necessidade concreta.

Essas pendências não fazem parte da aceitação desta spec.

## 16. Referências

- [ADR-009 — PostgreSQL como banco de dados em rede](../adr/0009-postgresql-banco-em-rede.md)
- [SPEC-0008 — Migração do SQLite para PostgreSQL](0008-migracao-postgresql.md)
- [Arquitetura do Axion](../architecture.md)
- [README do projeto](../../README.md)
- [Grafana — PostgreSQL data source](https://grafana.com/docs/grafana/latest/datasources/postgres/)
- [Grafana — Configure the PostgreSQL data source](https://grafana.com/docs/grafana/latest/datasources/postgres/configure/)
- [Grafana — Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- [Grafana — Run with Docker](https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/)
