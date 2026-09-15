# ADR-001 — Utilização de Python e FastAPI no backend

- Status: Aceita
- Data: 15/09/2026

## Contexto

O Axion necessita de um backend responsável pelas regras de negócio, gerenciamento
das ordens de produção, persistência de dados, comunicação com outros componentes
do sistema e integração com o módulo de Inteligência Computacional.

O projeto também utilizará algoritmos de otimização para realizar a programação
da produção, sendo necessário integrar esses algoritmos ao restante da aplicação.

A equipe possui conhecimento prévio em Python, tornando a linguagem comum entre
os integrantes e reduzindo a curva de aprendizado necessária durante o
desenvolvimento.

## Decisão

Python será utilizado como linguagem principal do backend e dos módulos de
Inteligência Computacional.

Para a construção da API será utilizado o framework FastAPI.

## Justificativa

Python foi escolhido principalmente pelos seguintes motivos:

- é uma linguagem conhecida por todos os integrantes da equipe;
- possui sintaxe simples e de fácil compreensão;
- facilita a leitura e manutenção do código entre os integrantes;
- possui amplo ecossistema de bibliotecas voltadas para algoritmos,
  otimização, análise de dados e Inteligência Computacional;
- permite utilizar a mesma linguagem tanto no backend quanto no módulo
  responsável pela otimização da produção.

FastAPI foi escolhido por fornecer uma estrutura simples para desenvolvimento
de APIs utilizando Python, além de possuir integração com type hints,
validação de dados e geração automática de documentação da API através
do padrão OpenAPI.

## Alternativas consideradas

### Flask

Também permitiria a criação do backend utilizando Python.

Entretanto, FastAPI oferece recursos como validação baseada em tipos e
documentação automática de APIs de forma integrada, reduzindo a quantidade
de configuração necessária.

### Java com Spring Boot

É uma alternativa adequada para aplicações backend robustas.

Entretanto, sua utilização introduziria uma segunda linguagem principal no
projeto, enquanto os algoritmos de Inteligência Computacional continuariam
provavelmente sendo desenvolvidos em Python.

A utilização de Python em ambos os componentes reduz a complexidade de
integração e facilita a colaboração entre os integrantes.

## Consequências

### Positivas

- menor curva de aprendizado para a equipe;
- maior facilidade de compartilhamento de conhecimento;
- integração direta entre backend e algoritmos de otimização;
- grande disponibilidade de bibliotecas científicas e de otimização;
- documentação automática dos endpoints;
- desenvolvimento rápido de APIs.

### Negativas

- Python possui menor desempenho computacional bruto que algumas linguagens
  compiladas;
- operações computacionalmente muito pesadas podem exigir bibliotecas
  especializadas ou execução separada do processo principal da API;
- a utilização da mesma aplicação para API e algoritmos pesados deverá ser
  analisada para evitar que cálculos longos bloqueiem requisições.

## Revisão da decisão

A decisão poderá ser reavaliada caso sejam identificados requisitos de
desempenho, integração ou infraestrutura que não sejam adequadamente
atendidos pela solução escolhida.