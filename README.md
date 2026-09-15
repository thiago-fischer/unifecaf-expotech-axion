# Axion — Linha de Produção Inteligente

O **Axion** é uma plataforma para planejamento, otimização e acompanhamento de uma linha de produção inteligente em escala reduzida.

O sistema permite cadastrar produtos, criar ordens de produção, otimizar a sequência das operações e acompanhar a execução física em uma maquete automatizada.

A proposta integra software, dispositivos embarcados, inteligência computacional, rastreabilidade, observabilidade e segurança de rede.

## Sobre o projeto

Em uma linha de produção com diferentes produtos, cada item pode exigir máquinas, operações e tempos de processamento distintos.

Quando a sequência de produção não é bem planejada, podem surgir problemas como máquinas ociosas, gargalos, filas entre etapas e aumento do tempo total necessário para concluir uma ordem.

O Axion busca resolver esse problema por meio de um sistema capaz de planejar automaticamente a produção, considerando os produtos solicitados, suas quantidades, as etapas produtivas, o tempo de processamento em cada máquina e a disponibilidade dos recursos.

## Principais funcionalidades

- Cadastro de produtos e etapas produtivas.
- Criação de produtos personalizados.
- Criação de ordens de produção.
- Otimização da programação da produção.
- Comunicação com dispositivos embarcados.
- Acompanhamento do estado das máquinas.
- Rastreabilidade das matérias-primas.
- Validação final das unidades produzidas.
- Coleta e visualização de métricas do processo.

## Arquitetura do software

O sistema será composto por módulos integrados, cada um com uma responsabilidade específica.

### Frontend

Interface responsável pela interação com o usuário.

Funcionalidades previstas:

- cadastro e seleção de produtos;
- criação de produtos personalizados;
- criação de ordens de produção;
- acompanhamento da produção;
- visualização do estado das máquinas;
- acompanhamento da rastreabilidade;
- visualização da validação final.

### Backend

Camada responsável pelas regras do sistema e pela integração entre os componentes.

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

Ela será composta por estações de processamento e por um mecanismo automatizado para movimentação da matéria-prima entre elas.

No escopo inicial, as máquinas não realizarão transformação física sobre a matéria-prima. O processamento será representado por tempo de operação e por displays instalados nas estações.

Os displays poderão exibir:

- nome do produto em processamento;
- etapa atual;
- estado da máquina;
- tempo restante da operação.

## Rastreabilidade

Cada unidade física de matéria-prima possuirá uma identificação individual.

No início do processo, essa identificação será lida e associada ao produto que a matéria-prima deverá representar durante a ordem de produção.

Exemplo:

```text
MAT-001 → Produto A
MAT-002 → Produto A
MAT-003 → Produto B
```

Ao final do processo, uma nova leitura será realizada para validar se a unidade corresponde ao item esperado e se percorreu corretamente as etapas definidas.

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
