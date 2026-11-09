# ADR-009 — PostgreSQL como banco de dados em rede

- Status: Aceita
- Data: 09/11/2026
- Substitui: ADR-002

## Contexto

O Axion utiliza atualmente SQLite, conforme a ADR-002. Essa escolha atendeu ao
desenvolvimento inicial porque o banco era local ao processo da API, havia pouca
concorrência e não existia outro consumidor dos dados.

A arquitetura planejada passou a incluir serviços independentes conectados por
rede. O backend continuará responsável pelas regras de negócio e pela escrita
dos dados. O Grafana deverá executar em container e consultar dados persistidos
com uma conexão própria. A maquete também terá dispositivos trocando informações
pela rede com o servidor para permitir observação e experimentos da disciplina
de Telecomunicações.

SQLite não oferece um serviço cliente-servidor acessível por TCP. Compartilhar o
arquivo SQLite entre processos ou containers não fornece o modelo de concorrência,
isolamento e operação em rede necessário para esse cenário. Os critérios de
reavaliação registrados na ADR-002 foram, portanto, atingidos.

Esta decisão trata somente do SGBD e da forma de conexão. Ela não define o
protocolo dos dispositivos, as tabelas futuras de telemetria, os dashboards do
Grafana nem uma implantação em cloud.

## Decisão

Adotar PostgreSQL como banco relacional do Axion e retirar SQLite dos ambientes
de execução e dos testes do backend após a migração.

- A API e o Alembic usarão SQLAlchemy 2.x com acesso síncrono e o driver Psycopg
  3, preservando a ADR-005 nos demais aspectos.
- A conexão será configurada por uma URL PostgreSQL fornecida por variável de
  ambiente. Credenciais reais não serão versionadas.
- O PostgreSQL será disponibilizado inicialmente por container, com volume
  persistente, verificação de saúde e rede nomeada do projeto.
- O histórico Alembic existente será preservado e validado em PostgreSQL. Não
  serão reescritas migrations já integradas apenas para trocar o SGBD.
- A aplicação continuará sem executar `create_all()` na inicialização. A
  preparação do banco continuará explícita por `alembic upgrade head`.
- O backend será o único componente autorizado a alterar dados de domínio por
  regras de negócio. O Grafana receberá, quando for integrado, uma credencial
  própria somente de leitura e acesso apenas às tabelas ou views necessárias.
- Dispositivos embarcados não acessarão o PostgreSQL diretamente. Eles trocarão
  mensagens com o backend pelo protocolo que vier a ser decidido em ADR própria.
- O serviço do banco não será exposto à rede local por padrão. Acesso externo ao
  host, se necessário em um experimento de Telecomunicações, exigirá configuração
  explícita de interface, firewall, autenticação e escopo do laboratório.

PostgreSQL será o único SGBD suportado após a conclusão da spec de migração. Não
será mantida compatibilidade permanente com dois dialetos, pois isso ampliaria a
matriz de testes e poderia ocultar diferenças de integridade e concorrência.

## Justificativa

PostgreSQL fornece o modelo cliente-servidor requerido para consumidores em
processos e containers separados. Também oferece concorrência de escrita,
transações e controle de usuários mais adequados à evolução do backend e à
integração de observabilidade.

A permanência no ecossistema relacional preserva os models, repositories,
services, schemas Pydantic e a maior parte das migrations existentes. SQLAlchemy
e Alembic já abstraem parte relevante da troca de dialeto, enquanto Psycopg 3
fornece um driver PostgreSQL mantido e compatível com o acesso síncrono decidido
para o MVP.

A conexão direta do Grafana ao banco é aceitável para consultas de observação
desde que use menor privilégio. Ela não autoriza o Grafana a executar operações
de negócio nem transforma as tabelas atuais em um modelo definitivo de métricas.

## Alternativas consideradas

### Manter SQLite e compartilhar o arquivo

Rejeitada. O arquivo não deve ser compartilhado por volume de rede como forma de
integração entre serviços. Essa opção mantém limitações de concorrência e não
representa uma arquitetura cliente-servidor para os experimentos planejados.

### Manter SQLite na API e exportar dados para outro banco do Grafana

Rejeitada para o escopo atual. Exigiria replicação ou ETL, criaria duas fontes de
verdade e aumentaria a operação antes de existir necessidade demonstrada de um
armazenamento analítico separado.

### MySQL/MariaDB

Atenderia ao acesso em rede, mas PostgreSQL foi preferido por sua integração com
SQLAlchemy, Alembic e Grafana, por seus recursos de integridade e por permitir
evoluções futuras sem introduzir outro ecossistema de banco ao projeto.

### Banco gerenciado em cloud

Permanece uma alternativa de implantação futura. A escolha de provedor e cloud
ainda está em aberto e não é necessária para validar a migração local em rede.

### Acesso assíncrono ao PostgreSQL

Não adotado nesta mudança. Trocar simultaneamente SGBD e modelo de concorrência
ampliaria o risco e não há medição que justifique abandonar o acesso síncrono da
ADR-005.

## Consequências

### Positivas

- API, Alembic e Grafana poderão conectar-se ao banco por TCP e DNS.
- Melhor suporte a conexões concorrentes e a futuros processos independentes.
- Usuários e permissões distintos para escrita da aplicação e leitura do Grafana.
- Ambiente reproduzível por container e migrations versionadas.
- Cenário real de rede para observação, segurança e Telecomunicações.

### Negativas

- O desenvolvimento passa a depender de um serviço PostgreSQL em execução.
- Credenciais, volume persistente, backup e disponibilidade precisam ser operados.
- Testes de integração ficam mais lentos e exigem PostgreSQL descartável.
- SQL e testes específicos de SQLite precisam ser removidos ou adaptados.
- A transferência de dados existentes exige uma etapa controlada e validação de
  chaves, referências e sequências.

## Riscos e controles

- **Credenciais expostas:** usar variáveis de ambiente, exemplos sem segredos e
  credenciais distintas para aplicação e Grafana.
- **Banco exposto indevidamente:** limitar a publicação de porta ao host local no
  ambiente padrão e documentar qualquer exposição de laboratório.
- **Grafana com acesso excessivo:** conceder somente `SELECT` nas relações
  necessárias e não reutilizar o usuário da aplicação.
- **Perda ou duplicação de dados:** migrar a partir de cópia do SQLite, interromper
  escritas durante o corte e comparar contagens e referências antes da troca.
- **Diferenças entre dialetos:** executar todo o histórico Alembic e a suíte do
  backend em PostgreSQL, incluindo constraints e upgrade/downgrade descartáveis.

## Plano de adoção

A SPEC-0008 detalha a implementação e os critérios de aceite. Em resumo:

1. preparar PostgreSQL local por container e configuração segura;
2. adaptar driver, settings, engine, Alembic e testes;
3. validar o histórico completo de migrations no novo dialeto;
4. transferir e conferir dados existentes que precisem ser preservados;
5. atualizar documentação e CI;
6. retirar o caminho SQLite após o corte validado.

A decisão está aceita, mas sua implementação depende da SPEC-0008. Até a
conclusão da migração, SQLite continua sendo o banco executado pelo código atual.

## Referências

- [ADR-002 — Utilização de SQLite como banco inicial](0002-sqlite.md)
- [ADR-005 — SQLAlchemy, Pydantic e Alembic](0005-sqlalchemy-pydantic-alembic.md)
- [SPEC-0008 — Migração do SQLite para PostgreSQL](../specs/0008-migracao-postgresql.md)

