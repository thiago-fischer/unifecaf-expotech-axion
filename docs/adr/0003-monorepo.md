# ADR-003 — Utilização de Monorepo

- Status: Aceita
- Data: 15/09/2026

## Contexto

O Axion é composto por diferentes partes que precisam funcionar de forma integrada, incluindo frontend, backend, módulo de Inteligência Computacional, dispositivos embarcados, banco de dados e infraestrutura.

Apesar de possuírem responsabilidades diferentes, esses componentes fazem parte do mesmo produto e serão desenvolvidos pela mesma equipe.

O projeto também exige colaboração entre os integrantes, revisão de código, documentação e integração contínua.

Diante disso, foi necessário definir se os diferentes componentes seriam armazenados em repositórios independentes ou em um único repositório.

## Decisão

O Axion será desenvolvido utilizando uma estratégia de monorepo.

Todos os principais componentes do projeto serão mantidos dentro de um único repositório Git, separados por diretórios de acordo com suas responsabilidades.

Uma possível estrutura inicial será:

```text
axion/
├── backend/
├── frontend/
├── optimizer/
├── firmware/
├── infrastructure/
├── docs/
└── README.md
```

A estrutura poderá evoluir conforme novos componentes forem adicionados ao projeto.

## Justificativa

O monorepo foi escolhido principalmente porque todos os componentes pertencem ao mesmo sistema e possuem forte relação entre si.

Manter o projeto em um único repositório facilita:

- a visualização completa da solução;
- a integração entre frontend, backend, algoritmos e dispositivos;
- o compartilhamento da documentação;
- a revisão de alterações que envolvem mais de um componente;
- o acompanhamento da evolução do projeto;
- a organização das Pull Requests;
- a configuração centralizada de práticas de colaboração;
- a criação de pipelines de CI/CD para os diferentes componentes.

Além disso, como o projeto será desenvolvido por uma equipe relativamente pequena, a separação em múltiplos repositórios adicionaria uma complexidade de gerenciamento que não apresenta benefícios significativos neste momento.

## Alternativas consideradas

### Múltiplos repositórios

Cada componente poderia possuir seu próprio repositório, por exemplo:

- axion-backend;
- axion-frontend;
- axion-optimizer;
- axion-firmware;
- axion-infrastructure.

Essa abordagem permitiria maior independência entre os componentes.

Entretanto, como todos fazem parte do mesmo projeto e serão desenvolvidos pela mesma equipe, essa separação aumentaria a quantidade de repositórios, configurações, documentações e fluxos de Pull Request que precisariam ser mantidos.

Também poderia dificultar alterações que dependam de modificações simultâneas em mais de um componente.

## Consequências

### Positivas

- visão centralizada de todo o projeto;
- facilidade para localizar código e documentação;
- simplificação do gerenciamento do repositório;
- maior facilidade para mudanças que envolvam vários componentes;
- histórico de evolução do projeto centralizado;
- issues e Pull Requests concentrados em um único local;
- maior facilidade para novos integrantes compreenderem a solução completa;
- possibilidade de centralizar configurações de CI/CD e qualidade de código.

### Negativas

- o repositório poderá crescer conforme novos componentes forem adicionados;
- pipelines de CI/CD precisarão identificar quais partes do projeto foram alteradas;
- será necessário definir uma organização clara dos diretórios;
- alterações independentes de componentes diferentes compartilharão o mesmo histórico Git;
- permissões de acesso não poderão ser separadas facilmente por componente.

## Organização

Cada componente deverá possuir um diretório próprio e manter seus arquivos, dependências e configurações isolados sempre que possível.

Por exemplo, o backend poderá possuir seu próprio arquivo de dependências Python, enquanto o frontend e o firmware poderão utilizar seus próprios mecanismos de gerenciamento.

O diretório `docs/` será utilizado para documentação compartilhada do projeto, incluindo ADRs, diagramas e demais decisões arquiteturais.

## CI/CD

Apesar de utilizar um único repositório, os diferentes componentes poderão possuir processos de validação independentes.

Os pipelines deverão, sempre que possível, executar apenas as validações relacionadas aos componentes alterados.

Por exemplo:

- alterações em `backend/` executam testes e lint do backend;
- alterações em `frontend/` executam validações do frontend;
- alterações em `firmware/` executam validações relacionadas ao firmware.

## Critérios para reavaliação

A utilização de monorepo poderá ser reavaliada caso:

- os componentes passem a possuir ciclos de desenvolvimento completamente independentes;
- diferentes equipes sejam responsáveis por partes distintas do sistema;
- o tamanho do repositório passe a prejudicar significativamente o desenvolvimento;
- sejam necessárias permissões de acesso diferentes para determinados componentes;
- algum componente passe a ser distribuído ou mantido como um projeto independente.
