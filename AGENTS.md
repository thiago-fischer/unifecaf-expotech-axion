# AGENTS.md — Axion

## Contexto do projeto

O Axion é uma linha de produção inteligente em escala reduzida,
desenvolvida para a ExpoTech 2026.2, na categoria NEXUS.

O sistema recebe ordens com produtos e quantidades, otimiza a programação
da produção e acompanha sua execução em uma maquete automatizada.

O objetivo principal da otimização é minimizar o tempo total da ordem,
respeitando a sequência das etapas e a disponibilidade das máquinas.

## Documentação de referência

Consulte conforme a tarefa:

- README.md: apresentação e funcionalidades.
- CONTRIBUTING.md: regras de colaboração, branches e Pull Requests.
- docs/visao-geral.md: escopo, funcionamento e decisões em aberto.
- docs/architecture.md: componentes e tecnologias.
- docs/adr/: decisões arquiteturais e suas justificativas.

Respeite as ADRs com status "Aceita".
Se houver divergências entre documentos, explicite a inconsistência
e use a ADR aceita correspondente como referência técnica.

## Escopo do MVP

- Produtos possuem nome, sequência de etapas, máquinas e tempos.
- O usuário pode criar produtos personalizados.
- Ordens de produção especificam produtos e quantidades.
- Cada unidade física possui identificação individual e rastreabilidade.
- A validação final considera a identidade e o histórico da unidade.
- O transporte horizontal utiliza uma mesa deslizante acionada por fuso.
- O processamento nas estações é simulado por tempo e displays.
- Transformações físicas da matéria-prima estão fora do MVP.

Não trate alternativas em estudo como requisitos já aprovados.

## Arquitetura

- Organização em monorepo.
- Backend e otimização em Python.
- API HTTP com FastAPI.
- SQLite como banco de dados inicial.
- Frontend separado do backend.
- Grafana previsto para visualização de métricas.

No backend, mantenha as responsabilidades:

- Controllers: requisições, respostas e detalhes HTTP.
- Services: regras de negócio e coordenação de operações.
- Repositories: consultas e persistência.
- Models: entidades persistidas.
- Schemas Pydantic: estruturas de entrada e saída da API.

Controllers não devem acessar diretamente o banco.
Mantenha as regras de negócio independentes de HTTP sempre que possível.
Evite abstrações sem necessidade concreta.

## Decisões ainda em aberto

Consulte a documentação antes de escolher frontend, ORM, algoritmo de
otimização, protocolo de comunicação, identificação das peças ou cloud.

Quando a tarefa exigir uma dessas escolhas, documente a justificativa
e seu status. Não apresente uma proposta como decisão aceita.

## Implementação

- Examine a estrutura existente antes de criar arquivos ou diretórios.
- Os diagramas de diretórios representam uma estrutura planejada;
  verifique o que já existe no repositório.
- Preserve o padrão do módulo que estiver sendo alterado.
- Use type hints no código Python.
- Mantenha as alterações focadas no objetivo da tarefa.
- Preserve alterações locais que não pertençam à tarefa.
- Torne a estrutura do banco reproduzível por migrations,
  scripts SQL ou mecanismo equivalente.
- Atualize a documentação quando modificar o comportamento do sistema.

## Validação

- Identifique os comandos disponíveis nos arquivos do módulo.
- Execute os testes e verificações pertinentes à alteração.
- Para regras de negócio novas ou corrigidas, cubra os comportamentos
  relevantes com testes quando houver estrutura para isso.
- Se não houver testes automatizados, descreva a validação realizada.
- Diferencie validação por simulação de validação em hardware real.
- Não afirme que um teste passou sem executá-lo.

Ao configurar um módulo, documente seus comandos de instalação,
execução e validação no README correspondente.

## Git e colaboração

- Siga CONTRIBUTING.md.
- Faça alterações relevantes em uma branch separada da main.
- Use commits claros e descritivos.
- Pull Requests devem explicar motivo, alterações e validação.
- O merge exige revisão de pelo menos outro integrante.
- Registre mudanças arquiteturais relevantes em docs/adr/.

## Segurança

- Não versione senhas, tokens, chaves ou arquivos .env reais.
- Use variáveis de ambiente e exemplos sem credenciais.
- Não inclua dependências instaladas, caches ou arquivos temporários.

## Comunicação

- Responda em português.
- Explique o que mudou, como foi validado e quais pendências existem.
- Distinga funcionalidades implementadas de funcionalidades planejadas.
