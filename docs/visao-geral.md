# Axion — Linha de Produção Inteligente

## 1. Visão Geral

A Axion é um projeto de automação e otimização industrial que propõe a construção de uma linha de produção inteligente em escala reduzida.

O sistema será responsável por receber uma demanda contendo diferentes tipos e quantidades de produtos e determinar automaticamente uma programação eficiente para sua produção.

A solução buscará reduzir o tempo total necessário para concluir uma ordem, aproveitando da melhor forma possível as máquinas disponíveis e permitindo que diferentes etapas de produção sejam executadas simultaneamente quando houver disponibilidade de recursos.

O planejamento gerado pelo sistema será executado fisicamente em uma maquete automatizada, integrando software, dispositivos embarcados, comunicação em rede, inteligência computacional, monitoramento e observabilidade.

## 2. Problema

Em uma linha de produção com diferentes produtos, cada item pode exigir máquinas, operações e tempos de processamento distintos.

Uma sequência inadequada de produção pode ocasionar máquinas ociosas, gargalos, filas entre etapas e aumento do tempo necessário para concluir uma ordem.

O problema central do projeto consiste, portanto, em determinar como organizar as operações de uma ordem de produção de maneira eficiente, considerando os recursos disponíveis e a possibilidade de execução simultânea em diferentes máquinas.

## 3. Objetivo

O objetivo principal da Axion é desenvolver uma linha de produção inteligente capaz de planejar e executar automaticamente uma ordem produtiva.

A partir da quantidade solicitada de cada produto, técnicas de Inteligência Computacional serão utilizadas para encontrar uma programação que busque minimizar o tempo total de produção e maximizar a utilização dos recursos disponíveis.

O resultado da otimização deverá ser executado pela maquete física e acompanhado pelo sistema.

## 4. Funcionamento Conceitual

O usuário informará ao sistema uma ordem de produção contendo os produtos desejados e suas respectivas quantidades.

Cada tipo de produto possuirá uma sequência de operações e tempos associados às máquinas necessárias para sua fabricação.

O módulo de otimização avaliará possíveis programações e determinará uma estratégia de produção.

A linha física executará esse planejamento, movimentando a matéria-prima entre as estações e permitindo o processamento simultâneo em diferentes máquinas sempre que possível.

Ao final do processo, haverá uma etapa destinada à verificação da qualidade do produto produzido.

**Fluxo geral:**

`Ordem de produção → Otimização → Planejamento → Execução física → Controle de qualidade → Produto final`

## 5. Inteligência Computacional

A Inteligência Computacional será aplicada ao problema de programação da produção.

O sistema deverá considerar características como quantidade de produtos, sequência de operações, tempo de processamento, disponibilidade das máquinas e possibilidade de operações simultâneas.

O principal indicador de otimização será o tempo total necessário para concluir uma ordem de produção, podendo posteriormente serem considerados outros fatores.

O algoritmo específico de otimização ainda será definido durante a etapa de desenvolvimento e experimentação.

## 6. Maquete e Automação

O projeto contará com uma representação física de uma linha de produção.

A maquete deverá possuir diferentes estações de processamento e um mecanismo automatizado para movimentação da matéria-prima entre elas.

Atualmente, uma das principais alternativas estudadas para o transporte é a utilização de uma mesa ou eixo linear deslizante. A solução mecânica definitiva ainda será definida após testes e prototipação.

As máquinas poderão realizar operações reais ou representativas sobre a matéria-prima. Entre as possibilidades estudadas está a realização de algum tipo de transformação física visível, como pintura ou outra operação de processamento.

A forma definitiva dessa transformação permanece em aberto.

## 7. Controle de Qualidade

Após as etapas de produção, o produto passará por uma etapa de inspeção.

O objetivo será determinar se o item produzido atende aos critérios esperados antes de ser direcionado ao estoque ou finalização.

A tecnologia utilizada para essa inspeção ainda será definida, podendo envolver sensores ou outras técnicas compatíveis com a transformação física escolhida para o produto.

## 8. Sistema de Software

A solução contará com diferentes componentes integrados.

O frontend será responsável pela interação com o usuário, incluindo criação e acompanhamento das ordens de produção.

O backend será responsável pelas regras do sistema, integração entre os componentes, gerenciamento das ordens e comunicação com o módulo de otimização e com a linha física.

Os dispositivos embarcados, utilizando Arduino, ESP32 ou tecnologia equivalente, serão responsáveis pelo controle das máquinas, sensores, atuadores e mecanismos de movimentação.

O sistema também contará com persistência de dados para armazenamento das informações relacionadas à produção.

As tecnologias específicas utilizadas no frontend, backend, banco de dados e firmware serão definidas posteriormente.

## 9. Observabilidade e Métricas

A solução utilizará Grafana para acompanhamento de métricas do processo.

Entre os indicadores que poderão ser acompanhados estão:

- tempo total de produção;
- utilização das máquinas;
- tempo ocioso;
- quantidade produzida;
- taxa de aprovação no controle de qualidade;
- falhas;
- outras métricas relevantes.

O conjunto definitivo de métricas será definido conforme a evolução do projeto.

## 10. Telecomunicações e Segurança de Rede

Os diferentes componentes da linha de produção funcionarão como dispositivos conectados, permitindo a comunicação entre máquinas, sistema central e demais componentes.

O projeto contemplará o monitoramento dessa comunicação e a análise da segurança da rede utilizada pela linha de produção.

Será demonstrado inicialmente um cenário contendo uma vulnerabilidade real de comunicação ou infraestrutura.

Essa vulnerabilidade será analisada e posteriormente mitigada, permitindo demonstrar a evolução:

`Comunicação vulnerável → Captura/análise → Vulnerabilidade identificada → Mitigação → Comunicação protegida`

Os protocolos, ferramentas, técnicas de captura e mecanismos de proteção ainda serão definidos durante o desenvolvimento.

## 11. Arquitetura de Software

O sistema possuirá uma arquitetura documentada que represente a integração entre interface, backend, persistência, inteligência computacional, observabilidade, dispositivos embarcados e infraestrutura de comunicação.

Padrões de projeto serão utilizados onde houver justificativa arquitetural.

A arquitetura definitiva e os padrões empregados serão definidos conforme a solução evoluir.

## 12. Open Source e Colaboração

O projeto será desenvolvido como software open source.

O repositório será utilizado para versionamento, documentação, colaboração entre os integrantes e revisão das alterações realizadas durante o desenvolvimento.

Licenciamento, estratégia de branches, fluxo de Pull Requests, versionamento e demais práticas de governança serão definidos ao longo da estruturação do repositório.

## 13. Cloud e CI/CD

Parte da solução será implantada em ambiente de nuvem.

O projeto também possuirá um processo de integração e entrega contínua responsável pela validação automatizada das alterações realizadas no código.

A plataforma de nuvem, estratégia de deploy, testes automatizados e demais tecnologias de infraestrutura ainda serão definidas.

## 14. Decisões Atualmente em Aberto

Neste estágio do projeto permanecem em definição:

- algoritmo de Inteligência Computacional;
- quantidade definitiva de máquinas;
- receitas e tempos definitivos dos produtos;
- mecanismo final de movimentação;
- transformação física aplicada à matéria-prima;
- método de controle de qualidade;
- protocolo de comunicação entre dispositivos;
- vulnerabilidade de rede que será estudada;
- tecnologias de frontend e backend;
- banco de dados;
- arquitetura definitiva;
- plataforma de cloud;
- estratégia de CI/CD;
- ferramentas e bibliotecas específicas.

Essas decisões não alteram o conceito central do projeto e serão definidas por meio de estudo, experimentação e prototipação.

## 15. Resultado Esperado

Ao final do projeto, espera-se possuir uma linha de produção inteligente em escala reduzida capaz de receber uma demanda, gerar uma programação otimizada, executar fisicamente o planejamento e apresentar informações sobre o desempenho do processo.

A demonstração deverá evidenciar a integração entre automação industrial, sistemas embarcados, Inteligência Computacional, software, persistência de dados, monitoramento e segurança de redes.
