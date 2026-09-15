# ADR-002 — Utilização de SQLite como banco de dados inicial

- Status: Aceita
- Data: 15/09/2026

## Contexto

O Axion necessita de persistência para armazenar informações como produtos,
ordens de produção, etapas produtivas, estados das máquinas, rastreabilidade
das matérias-primas e resultados das execuções.

Durante o desenvolvimento inicial e a demonstração do projeto, não é esperado
um grande número de usuários acessando ou alterando os dados simultaneamente.

O sistema será utilizado principalmente pela própria equipe e durante a
demonstração da maquete.

## Decisão

SQLite será utilizado como banco de dados relacional durante o desenvolvimento
inicial e no MVP do Axion.

## Justificativa

SQLite foi escolhido por apresentar baixa complexidade de configuração e
administração.

O banco não necessita de um servidor próprio e pode ser executado diretamente
pela aplicação.

Para o escopo inicial do Axion, não são esperados requisitos elevados de
concorrência, múltiplas instâncias da aplicação ou grande quantidade de
acessos simultâneos.

Dessa forma, a utilização de um SGBD cliente-servidor adicionaria complexidade
de infraestrutura sem apresentar benefícios significativos para o MVP.

## Alternativas consideradas

### PostgreSQL

Oferece maior capacidade para concorrência, múltiplos usuários e ambientes
distribuídos.

Entretanto, exige a configuração e manutenção de um serviço de banco de dados
separado.

Para o volume e utilização inicialmente previstos no Axion, essa complexidade
não é necessária.

### MySQL

Também atenderia aos requisitos de persistência da aplicação, porém possui
necessidade semelhante de infraestrutura e administração de um servidor de
banco de dados.

## Consequências

### Positivas

- configuração simples;
- nenhuma dependência de servidor de banco de dados;
- facilidade de execução local;
- facilidade para criação de ambientes de desenvolvimento;
- baixo consumo de recursos;
- facilita a demonstração do sistema em diferentes computadores.

### Negativas

- menor capacidade para múltiplas escritas simultâneas;
- limitações caso o sistema passe a utilizar várias instâncias do backend;
- pode não ser adequado caso o projeto evolua para uma aplicação com muitos
  usuários simultâneos;
- ambientes de cloud podem exigir cuidados adicionais para garantir
  persistência do arquivo do banco.

## Versionamento

O arquivo SQLite não será utilizado como principal mecanismo de versionamento
da estrutura do banco.

A estrutura do banco deverá ser reproduzível através de migrations,
scripts SQL ou outro mecanismo equivalente.

Um banco SQLite contendo dados de demonstração poderá eventualmente ser
mantido no repositório, caso isso facilite a execução e apresentação do projeto.

## Critérios para reavaliação

A adoção de outro SGBD deverá ser considerada caso o projeto passe a exigir:

- múltiplos usuários realizando operações simultâneas;
- várias instâncias do backend;
- maior volume de dados;
- necessidade de persistência distribuída em cloud;
- maior nível de concorrência de escrita;
- infraestrutura de produção permanente.

Nesse cenário, PostgreSQL será uma das alternativas avaliadas.