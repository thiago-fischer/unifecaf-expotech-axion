# Axion — Linha de Produção Inteligente

> **Versão do documento:** 0.2  
> **Status:** Em definição  
> **Última atualização:** 15/09/2026

## Histórico de versões

| Versão | Data | Alterações principais |
|---|---|---|
| 0.1 | 11/09/2026 | Definição inicial do conceito, otimização industrial, maquete e requisitos gerais. |
| 0.2 | 15/09/2026 | Definição do transporte horizontal por fuso, retirada da transformação física do MVP, inclusão de produtos configuráveis pelo usuário, displays nas máquinas e rastreabilidade/QA das matérias-primas. |

## 1. Visão Geral

A Axion é um projeto de automação e otimização industrial que propõe a construção de uma linha de produção inteligente em escala reduzida.

O sistema será responsável por receber uma demanda contendo diferentes tipos e quantidades de produtos e determinar automaticamente uma programação eficiente para sua produção.

A solução buscará reduzir o tempo total necessário para concluir uma ordem, aproveitando da melhor forma possível as máquinas disponíveis e permitindo que diferentes etapas de produção sejam executadas simultaneamente quando houver disponibilidade de recursos.

O planejamento gerado pelo sistema será executado fisicamente em uma maquete automatizada, integrando software, dispositivos embarcados, comunicação em rede, inteligência computacional, rastreabilidade, monitoramento e observabilidade.

## 2. Problema

Em uma linha de produção com diferentes produtos, cada item pode exigir máquinas, operações e tempos de processamento distintos.

Uma sequência inadequada de produção pode ocasionar máquinas ociosas, gargalos, filas entre etapas e aumento do tempo necessário para concluir uma ordem.

O problema central do projeto consiste, portanto, em determinar como organizar as operações de uma ordem de produção de maneira eficiente, considerando os recursos disponíveis, as dependências entre etapas e a possibilidade de execução simultânea em diferentes máquinas.

## 3. Objetivo

O objetivo principal da Axion é desenvolver uma linha de produção inteligente capaz de planejar e executar automaticamente uma ordem produtiva.

A partir da quantidade solicitada de cada produto, técnicas de Inteligência Computacional serão utilizadas para encontrar uma programação que busque minimizar o tempo total de produção e maximizar a utilização dos recursos disponíveis.

O resultado da otimização deverá ser executado pela maquete física e acompanhado pelo sistema.

Além dos produtos previamente cadastrados, o sistema deverá permitir que o usuário crie produtos personalizados, definindo seu nome, suas etapas e o tempo necessário em cada máquina.

## 4. Funcionamento Conceitual

O usuário poderá selecionar produtos previamente cadastrados ou criar um produto personalizado.

Cada produto será definido por uma sequência de etapas produtivas, indicando as máquinas pelas quais deverá passar e o tempo necessário em cada uma delas.

Com base nesses produtos, o usuário criará uma ordem de produção informando as respectivas quantidades.

O módulo de otimização avaliará possíveis programações e determinará uma estratégia de produção eficiente, buscando utilizar as máquinas disponíveis simultaneamente sempre que possível.

Antes do início do processo físico, cada unidade de matéria-prima será identificada e associada ao produto que deverá representar durante toda a produção.

A linha física executará o planejamento gerado, movimentando a matéria-prima entre as máquinas.

Ao final, uma etapa de rastreabilidade e validação verificará se a unidade física corresponde ao item inicialmente identificado e se o processo esperado foi concluído.

**Fluxo geral:**

`Cadastro/seleção de produtos → Demanda → Otimização → Identificação da matéria-prima → Execução física → Rastreabilidade → Validação final → Produto final`

## 5. Produtos e Ordens de Produção

O sistema possuirá um catálogo de produtos previamente cadastrados.

Cada produto será definido por:

- nome;
- sequência de etapas;
- máquina responsável por cada etapa;
- tempo de processamento em cada máquina.

Além dos produtos existentes no sistema, o usuário poderá criar produtos personalizados em tempo de execução.

Os produtos personalizados poderão ser utilizados normalmente nas ordens de produção juntamente com os produtos previamente cadastrados.

Uma ordem poderá, por exemplo, conter:

- Produto A: 3 unidades;
- Produto B: 2 unidades;
- Produto personalizado: 4 unidades.

A partir dessa demanda, o módulo de Inteligência Computacional deverá buscar uma programação eficiente para utilização das máquinas disponíveis.

## 6. Inteligência Computacional

A Inteligência Computacional será aplicada ao problema de programação da produção.

O sistema deverá considerar características como:

- quantidade de produtos;
- sequência de operações;
- tempo de processamento;
- disponibilidade das máquinas;
- dependências entre etapas;
- possibilidade de operações simultâneas.

O principal indicador de otimização será o tempo total necessário para concluir uma ordem de produção, podendo posteriormente serem considerados outros fatores.

O algoritmo específico de otimização ainda será definido durante a etapa de desenvolvimento e experimentação.

## 7. Maquete e Automação

O projeto contará com uma representação física de uma linha de produção.

A maquete deverá possuir diferentes estações de processamento e um mecanismo automatizado para movimentação da matéria-prima entre elas.

A movimentação horizontal da matéria-prima será realizada por meio de uma mesa deslizante acionada por fuso.

O mecanismo responsável pelo movimento vertical ainda está em estudo, assim como o sistema de captura da matéria-prima. Atualmente, uma das principais alternativas consideradas para a captura é a utilização de um eletroímã.

No escopo inicial, as máquinas não realizarão transformação física sobre a matéria-prima.

O processamento será representado conceitualmente por meio de displays instalados em cada estação, que poderão apresentar informações como:

- nome do produto em processamento;
- etapa atual;
- estado da máquina;
- tempo restante da operação.

Caso o desenvolvimento avance além do escopo mínimo planejado e exista tempo disponível, a realização de transformações físicas poderá ser reavaliada como evolução futura.

## 8. Rastreabilidade e Validação de Qualidade

Cada unidade física de matéria-prima possuirá uma identificação individual.

No início do processo, essa identificação será lida e associada pelo sistema ao produto que aquela matéria-prima deverá representar durante toda a ordem de produção.

Exemplo:

`MAT-001 → Produto A`  
`MAT-002 → Produto A`  
`MAT-003 → Produto B`

A identificação acompanhará logicamente a matéria-prima durante todas as etapas da linha.

Ao final do processo, uma nova leitura será realizada para validar a identidade da unidade e verificar se o item corresponde ao produto inicialmente associado.

O sistema também poderá verificar o histórico daquela unidade, incluindo:

- produto associado;
- ordem de produção;
- etapas executadas;
- ordem das etapas;
- possíveis falhas registradas.

O mecanismo definitivo de identificação ainda será definido. Entre as alternativas atualmente consideradas estão:

- código de barras;
- QR Code;
- RFID;
- visão computacional;
- combinação entre identificação visual por cor e um identificador individual.

O resultado dessa etapa será utilizado para classificar a unidade como aprovada ou reprovada.

## 9. Sistema de Software

A solução contará com diferentes componentes integrados.

O frontend será responsável pela interação com o usuário, incluindo:

- cadastro e seleção de produtos;
- criação de produtos personalizados;
- criação de ordens de produção;
- acompanhamento da produção;
- visualização do estado das máquinas;
- acompanhamento da rastreabilidade e validação final.

O backend será responsável pelas regras do sistema, integração entre os componentes, gerenciamento das ordens e comunicação com o módulo de otimização e com a linha física.

Os dispositivos embarcados, utilizando Arduino, ESP32 ou tecnologia equivalente, serão responsáveis pelo controle das máquinas, displays, sensores, atuadores e mecanismos de movimentação.

O sistema também contará com persistência de dados para armazenamento das informações relacionadas à produção.

As tecnologias específicas utilizadas no frontend, backend, banco de dados e firmware serão definidas posteriormente.

## 10. Observabilidade e Métricas

A solução utilizará Grafana para acompanhamento de métricas do processo.

Entre os indicadores que poderão ser acompanhados estão:

- tempo total de produção;
- utilização das máquinas;
- tempo ocioso;
- quantidade produzida;
- taxa de aprovação na validação final;
- falhas;
- outras métricas relevantes.

O conjunto definitivo de métricas será definido conforme a evolução do projeto.

## 11. Telecomunicações e Segurança de Rede

Os diferentes componentes da linha de produção funcionarão como dispositivos conectados, permitindo a comunicação entre máquinas, sistema central e demais componentes.

O projeto contemplará o monitoramento dessa comunicação e a análise da segurança da rede utilizada pela linha de produção.

Será demonstrado inicialmente um cenário contendo uma vulnerabilidade real de comunicação ou infraestrutura.

Essa vulnerabilidade será analisada e posteriormente mitigada, permitindo demonstrar a evolução:

`Comunicação vulnerável → Captura/análise → Vulnerabilidade identificada → Mitigação → Comunicação protegida`

Os protocolos, ferramentas, técnicas de captura e mecanismos de proteção ainda serão definidos durante o desenvolvimento.

## 12. Arquitetura de Software

O sistema possuirá uma arquitetura documentada que represente a integração entre interface, backend, persistência, inteligência computacional, observabilidade, dispositivos embarcados e infraestrutura de comunicação.

Padrões de projeto serão utilizados onde houver justificativa arquitetural.

A arquitetura definitiva e os padrões empregados serão definidos conforme a solução evoluir.

## 13. Open Source e Colaboração

O projeto será desenvolvido como software open source.

O repositório será utilizado para versionamento, documentação, colaboração entre os integrantes e revisão das alterações realizadas durante o desenvolvimento.

Licenciamento, estratégia de branches, fluxo de Pull Requests, versionamento e demais práticas de governança serão definidos ao longo da estruturação do repositório.

## 14. Cloud e CI/CD

Parte da solução será implantada em ambiente de nuvem.

O projeto também possuirá um processo de integração e entrega contínua responsável pela validação automatizada das alterações realizadas no código.

A plataforma de nuvem, estratégia de deploy, testes automatizados e demais tecnologias de infraestrutura ainda serão definidas.

## 15. Decisões Atualmente em Aberto

Neste estágio do projeto permanecem em definição:

- algoritmo de Inteligência Computacional;
- quantidade definitiva de máquinas;
- configuração final das máquinas;
- receitas e tempos dos produtos previamente cadastrados;
- mecanismo de movimento vertical;
- mecanismo definitivo de captura da matéria-prima;
- tecnologia de identificação e rastreabilidade;
- protocolo de comunicação entre dispositivos;
- vulnerabilidade de rede que será estudada;
- tecnologias de frontend e backend;
- banco de dados;
- arquitetura definitiva;
- plataforma de cloud;
- estratégia de CI/CD;
- ferramentas e bibliotecas específicas.

Essas decisões não alteram o conceito central do projeto e serão definidas por meio de estudo, experimentação e prototipação.

## 16. Evoluções Futuras

Caso o projeto avance além do escopo mínimo planejado e exista tempo hábil, poderão ser avaliadas funcionalidades adicionais.

Entre as possibilidades atualmente consideradas está a realização de algum tipo de transformação física sobre a matéria-prima durante as etapas de produção.

Essa funcionalidade não faz parte do MVP atual e sua eventual implementação dependerá do andamento do projeto.

## 17. Resultado Esperado

Ao final do projeto, espera-se possuir uma linha de produção inteligente em escala reduzida capaz de:

- receber uma demanda de produção;
- trabalhar com produtos previamente cadastrados ou criados pelo usuário;
- gerar uma programação otimizada;
- executar fisicamente o planejamento;
- movimentar e rastrear individualmente as matérias-primas;
- representar visualmente o processamento em cada máquina;
- validar a unidade produzida ao final da linha;
- apresentar informações e métricas sobre o desempenho do processo.

A demonstração deverá evidenciar a integração entre automação industrial, sistemas embarcados, Inteligência Computacional, software, persistência de dados, rastreabilidade, observabilidade e segurança de redes.
