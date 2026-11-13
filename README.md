# Axion — Linha de Produção Inteligente

O **Axion** é uma plataforma para planejamento, otimização e acompanhamento de uma linha de produção inteligente em escala reduzida.

O sistema tem como objetivo cadastrar produtos, criar ordens de produção, otimizar a sequência das operações e acompanhar a execução física em uma maquete automatizada.

**Implementado:** backend local com cadastro, listagem e consulta de máquinas
e produtos com receitas completas, além de ordens com produtos e quantidades,
PostgreSQL em container e migrations Alembic, conforme as SPEC-0001, SPEC-0003,
SPEC-0004 e SPEC-0008.
O planejamento transitório da SPEC-0005 usa AG obrigatório e certificação
CP-SAT, com operações e métricas para Gantt. A execução física permanece prevista.
O [frontend React](frontend/README.md), conforme a SPEC-0006, permite usar
localmente os catálogos, ordens e planejamento em português, com Gantt por
máquina, tabela de operações recolhível e identificação de resultados sem prova de ótimo.
Veja os comandos de instalação,
execução e testes no [README do backend](backend/README.md).
As demais funcionalidades descritas abaixo permanecem planejadas.

A proposta integra software, dispositivos embarcados, inteligência computacional, rastreabilidade, observabilidade e segurança de rede.

## Execução completa com Docker Compose

O Compose da raiz constrói e inicia o frontend, o backend e o PostgreSQL. Ele
também aplica as migrations Alembic em uma etapa separada antes de liberar a
API. O pacote Python local de otimização é incluído na imagem do backend.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

No Linux/macOS, use `cp .env.example .env`. Depois que os serviços estiverem
saudáveis, acesse a interface em <http://127.0.0.1:5173> e a documentação da
API em <http://127.0.0.1:8000/docs>. As portas podem ser alteradas no `.env`.
O frontend serve o build estático pelo Nginx e encaminha `/api` internamente
para o backend, sem expor o PostgreSQL à rede local.

Para executar em segundo plano ou encerrar:

```powershell
docker compose up --build -d
docker compose down
```

O volume `axion_postgres_data` é preservado por `docker compose down`. Não use
`docker compose down -v` se os dados locais precisarem ser mantidos.

## Sobre o projeto

Em uma linha de produção com diferentes produtos, cada item pode exigir máquinas, operações e tempos de processamento distintos.

Quando a sequência de produção não é bem planejada, podem surgir problemas como máquinas ociosas, gargalos, filas entre etapas e aumento do tempo total necessário para concluir uma ordem.

O Axion busca resolver esse problema por meio de um sistema capaz de planejar automaticamente a produção, considerando os produtos solicitados, suas quantidades, as etapas produtivas, o tempo de processamento em cada máquina e a disponibilidade dos recursos.

## Funcionalidades do projeto

- Cadastro de produtos e etapas produtivas: implementado na API e no frontend.
- Criação de produtos personalizados: implementada na API e no frontend.
- Criação de ordens de produção: implementada na API e no frontend.
- Otimização da programação: implementada em software, com consulta pelo frontend.
- Comunicação com dispositivos embarcados: planejada.
- Acompanhamento do estado das máquinas: planejado.
- Rastreabilidade das matérias-primas: planejada.
- Validação final das unidades produzidas: planejada.
- Coleta e visualização de métricas do processo físico: planejadas.

## Arquitetura do software

O sistema será composto por módulos integrados, cada um com uma responsabilidade específica.

### Frontend

Interface responsável pela interação com o usuário.

Implementado em React com TypeScript e Vite para uso local. Cadastro e consulta
de máquinas, produtos e ordens, além de planejamento em software, estão disponíveis.
Consulte o [README do frontend](frontend/README.md) e a
[ADR-007](docs/adr/0007-react-frontend.md). Acompanhamento físico e rastreabilidade
continuam planejados.

Funcionalidades do frontend, incluindo evoluções previstas:

- cadastro e seleção de produtos;
- criação de produtos personalizados;
- criação de ordens de produção;
- acompanhamento da produção;
- visualização do estado das máquinas;
- acompanhamento da rastreabilidade;
- visualização da validação final.

### Backend

Camada responsável pelas regras do sistema e pela integração entre os componentes.

Tecnologias definidas para implementação: **Python e FastAPI**, **Pydantic**
para os schemas da API, **SQLAlchemy 2.x** e **Alembic** para persistência.
O acesso ao banco é síncrono no MVP, com **PostgreSQL** e Psycopg 3. A decisão
está na [ADR-009](docs/adr/0009-postgresql-banco-em-rede.md) e a implementação
na [SPEC-0008](docs/specs/0008-migracao-postgresql.md). Veja também a
[ADR-005](docs/adr/0005-sqlalchemy-pydantic-alembic.md).

Responsabilidades previstas:

- gerenciamento de produtos;
- gerenciamento de ordens de produção;
- controle das etapas produtivas;
- comunicação com o módulo de otimização;
- comunicação com a linha física;
- persistência das informações do sistema.

### Módulo de otimização

Responsável por gerar uma programação eficiente para execução das ordens de produção.

O módulo deverá considerar:

- quantidade de produtos;
- sequência de operações;
- tempo de processamento;
- disponibilidade das máquinas;
- dependências entre etapas;
- possibilidade de operações simultâneas.

O principal indicador de otimização será o tempo total necessário para concluir uma ordem de produção.

### Firmware e dispositivos embarcados

Responsáveis pelo controle dos componentes físicos da maquete, como sensores, atuadores, displays, mecanismos de movimentação e estações de processamento.

Poderão ser utilizados Arduino, ESP32 ou tecnologias equivalentes.

### Banco de dados

Responsável pela persistência das informações do sistema, incluindo produtos, etapas produtivas, ordens de produção, matérias-primas identificadas, histórico de execução, falhas e métricas.

### Observabilidade

Responsável pelo acompanhamento de indicadores do processo produtivo.

Métricas previstas:

- tempo total de produção;
- utilização das máquinas;
- tempo ocioso;
- quantidade produzida;
- taxa de aprovação na validação final;
- falhas registradas.

A ferramenta prevista para acompanhamento das métricas é o **Grafana**.

### Segurança de rede

Responsável pela análise da comunicação entre os componentes conectados da linha de produção.

O projeto deverá demonstrar um cenário com uma vulnerabilidade real de comunicação ou infraestrutura, seguido de análise e mitigação.

## Maquete

A maquete representa uma linha de produção inteligente em escala reduzida.

O [controlador simulado](controller/README.md) já recebe comandos por HTTP
e permite testar o percurso das peças sem hardware.

A maquete física comportará até 10 peças e terá três máquinas de processamento
e uma estação de revisão de qualidade (QA). A mesa deslizante acionada por fuso
fará o transporte horizontal dos cubos metálicos, coletados por eletroímã.
O servidor gerará e otimizará a ordem de produção (OP) e enviará os comandos
à maquete na sequência planejada. [ADR-010](docs/adr/0010-maquete-fisica.md)

No escopo inicial, as máquinas não realizarão transformação física sobre a matéria-prima. O processamento será representado por tempo de operação e por displays instalados nas estações.

Os displays poderão exibir:

- nome do produto em processamento;
- etapa atual;
- estado da máquina;
- tempo restante da operação.

## Rastreabilidade

Cada cubo terá uma etiqueta RFID com identificador único. Após a coleta no
armazém, a maquete levará o cubo ao leitor. O sistema associará o ID à unidade
de produto correspondente na sequência planejada da OP.

Exemplo:

```text
MAT-001 → Produto A
MAT-002 → Produto A
MAT-003 → Produto B
```

Após o processamento, o cubo passará pela estação de QA para nova leitura e
conferência do histórico das etapas. A maquete terá duas vagas de estoque
auxiliar e esteiras de entrada e saída com um ponto fixo de acesso cada.
Peças aprovadas e rejeitadas compartilharão a esteira de saída, com o
resultado do QA vinculado ao RFID.

## Estrutura do repositório

```text
axion/
├── backend/
├── frontend/
├── firmware/
├── optimization/
├── monitoring/
├── docs/
├── .github/
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## Documentação

A documentação completa do projeto está disponível na pasta [`docs`](docs/).

A [SPEC-0007 — Maquete virtual 3D](docs/specs/0007-maquete-virtual.md)
descreve a demonstração animada implementada no frontend, com máquinas,
almoxarifado, transporte e estoque auxiliar. Funciona sem a API; integração
com o planejador e hardware permanece futura. Revisão por outro integrante pendente.

O planejamento está implementado conforme a
[SPEC-0005 — Otimização e cronograma da produção](docs/specs/0005-production-planning.md),
com AG obrigatório, verificação/certificação CP-SAT e saída para Gantt por máquina.
A [ADR-006](docs/adr/0006-ag-cpsat-production-planning.md) registra a proposta
técnica, ainda não aceita. Consulte o [núcleo](optimizer/README.md) e as
[medições de validação](docs/planning-validation.md). Nenhum plano autoriza
execução física nesta entrega.

## Contexto acadêmico

Projeto desenvolvido para a **ExpoTech 2026.2 — Missão 2050: Smart Home & Tecnologias do Futuro**, na categoria **NEXUS**, voltada ao curso de Engenharia da Computação.

O projeto busca atender aos pilares de:

- Open Source Contribution & Collaboration;
- Telecommunications & Network Security;
- Computational Intelligence & Algorithm Optimization;
- Software Architecture & Design Patterns;
- Cloud Computing for Software Development.

## Contribuição

O Axion é um projeto open source desenvolvido com fluxo de branches e Pull Requests.

As regras de contribuição estão descritas no arquivo [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licença

Este projeto está licenciado sob a licença MIT.

Consulte o arquivo [`LICENSE`](LICENSE) para mais detalhes.

## Equipe

Projeto desenvolvido por estudantes de Engenharia da Computação para a ExpoTech 2026.2.
