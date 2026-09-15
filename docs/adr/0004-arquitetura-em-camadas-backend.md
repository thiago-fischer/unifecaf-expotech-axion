# ADR-004 — Arquitetura em Camadas para o Backend

- Status: Aceita
- Data: 15/09/2026

## Contexto

O backend do Axion será responsável pelas regras de negócio, gerenciamento de produtos e ordens de produção, persistência de dados, integração com o módulo de Inteligência Computacional e comunicação com os demais componentes do sistema.

Com o início do desenvolvimento do CRUD de produtos, torna-se necessário definir uma organização arquitetural para o backend que facilite a manutenção, a evolução do sistema e a separação de responsabilidades.

A aplicação utilizará FastAPI como framework de backend, enquanto a interface de usuário será mantida em um frontend separado.

Por esse motivo, a aplicação não seguirá um MVC clássico completo dentro do backend, pois a camada de apresentação estará fora da API.

## Decisão

O backend do Axion utilizará uma arquitetura em camadas, inspirada na separação de responsabilidades do padrão MVC e adaptada para uma API REST.

A estrutura principal seguirá o fluxo:

```text
Request
   ↓
Controller
   ↓
Service
   ↓
Repository
   ↓
Model
   ↓
Banco de dados
```

A camada de apresentação, equivalente à View em uma arquitetura MVC tradicional, será responsabilidade do frontend.

## Estrutura Inicial

Uma possível organização inicial do backend será:

```text
backend/
└── app/
    ├── main.py
    ├── controllers/
    │   └── product_controller.py
    ├── services/
    │   └── product_service.py
    ├── repositories/
    │   └── product_repository.py
    ├── models/
    │   └── product.py
    ├── schemas/
    │   └── product_schema.py
    └── database/
        └── database.py
```

Essa estrutura poderá evoluir conforme novas necessidades surgirem durante o desenvolvimento.

## Responsabilidades das Camadas

### Controller

A camada Controller será responsável pela comunicação HTTP da aplicação.

Entre suas responsabilidades estarão:

- receber requisições;
- interpretar parâmetros;
- utilizar os schemas de entrada e saída;
- chamar os serviços correspondentes;
- retornar respostas HTTP adequadas.

Regras de negócio e acesso direto ao banco de dados não deverão ser implementados nessa camada.

### Service

A camada Service será responsável pelas regras de negócio da aplicação.

Entre suas responsabilidades estarão:

- validar regras relacionadas ao domínio;
- coordenar operações;
- combinar chamadas de diferentes repositories;
- controlar fluxos de negócio;
- integrar funcionalidades internas do sistema.

Essa camada deverá permanecer independente dos detalhes da camada HTTP sempre que possível.

### Repository

A camada Repository será responsável pelo acesso e persistência dos dados.

Entre suas responsabilidades estarão:

- criação de registros;
- consultas;
- atualizações;
- exclusões;
- abstração das operações realizadas no banco de dados.

O restante da aplicação deverá evitar acesso direto ao banco de dados quando essa responsabilidade puder ser centralizada em um repository.

### Model

A camada Model representará as entidades persistidas pela aplicação e suas estruturas relacionadas ao banco de dados.

Os modelos poderão representar entidades como:

- produtos;
- etapas de produção;
- máquinas;
- ordens de produção;
- matérias-primas;
- registros de rastreabilidade.

### Schema

Os schemas serão utilizados para representar estruturas de entrada e saída da API.

No FastAPI, essa responsabilidade será implementada principalmente com modelos Pydantic.

Essa separação permitirá diferenciar a representação utilizada pela API da representação utilizada internamente para persistência.

## Fluxo de uma Operação

Uma requisição para criação de produto poderá seguir o fluxo:

```text
POST /products
      ↓
ProductController
      ↓
ProductService
      ↓
ProductRepository
      ↓
SQLite
```

O Controller recebe os dados da requisição.

O Service aplica as regras de negócio necessárias.

O Repository realiza a persistência.

O resultado retorna pelas mesmas camadas até ser enviado ao cliente pela API.

## Justificativa

A arquitetura em camadas foi escolhida principalmente para separar responsabilidades e evitar que rotas da API concentrem regras de negócio e operações de persistência.

Essa organização facilita:

- leitura e compreensão do código;
- manutenção;
- criação de testes;
- reaproveitamento de regras de negócio;
- evolução do sistema;
- substituição de detalhes de infraestrutura;
- divisão de trabalho entre integrantes da equipe.

Além disso, a estrutura permite que funcionalidades futuras, como otimização, rastreabilidade e comunicação com dispositivos, sejam integradas sem concentrar toda a lógica diretamente nos endpoints da API.

## Alternativas Consideradas

### MVC Clássico

O MVC tradicional organiza a aplicação em Model, View e Controller.

Essa abordagem foi considerada, porém o frontend do Axion será separado do backend.

Por esse motivo, não existe uma camada View dentro da API FastAPI.

A separação de responsabilidades do MVC continuará sendo utilizada como referência, mas adaptada para uma arquitetura em camadas adequada a uma API REST.

### Rotas com acesso direto ao banco de dados

Uma alternativa mais simples seria implementar regras de negócio e operações de persistência diretamente nos endpoints do FastAPI.

Essa abordagem reduziria inicialmente a quantidade de arquivos e abstrações.

Entretanto, conforme o Axion crescer, essa estratégia aumentaria o acoplamento entre API, regras de negócio e persistência, dificultando manutenção e testes.

### Clean Architecture / Hexagonal Architecture

Arquiteturas como Clean Architecture ou Arquitetura Hexagonal oferecem maior desacoplamento entre domínio, infraestrutura e interfaces externas.

Entretanto, para o escopo inicial do projeto, essa abordagem poderia adicionar uma quantidade de abstrações superior à necessidade atual da equipe.

A arquitetura em camadas oferece uma separação adequada sem introduzir complexidade excessiva.

## Consequências

### Positivas

- melhor separação de responsabilidades;
- código mais organizado;
- maior facilidade de manutenção;
- maior facilidade para criação de testes;
- menor acoplamento entre HTTP, regras de negócio e banco de dados;
- possibilidade de reaproveitar services em diferentes contextos;
- estrutura consistente para crescimento do backend.

### Negativas

- maior quantidade de arquivos e diretórios;
- operações simples poderão atravessar várias camadas;
- exige disciplina da equipe para manter as responsabilidades corretamente separadas;
- existe risco de criação de abstrações desnecessárias caso as camadas sejam utilizadas sem necessidade.

## Regras de Organização

As seguintes regras deverão orientar o desenvolvimento inicial:

- Controllers não devem acessar diretamente o banco de dados;
- regras de negócio devem permanecer preferencialmente nos Services;
- operações de persistência devem permanecer nos Repositories;
- Models e Schemas devem possuir responsabilidades distintas;
- dependências entre camadas devem seguir, preferencialmente, o fluxo definido pela arquitetura;
- exceções à estrutura deverão ser justificadas quando necessárias.

## Critérios para Reavaliação

A arquitetura poderá ser reavaliada caso:

- o domínio do projeto se torne significativamente mais complexo;
- seja necessário aumentar o isolamento entre regras de negócio e infraestrutura;
- o backend passe a possuir múltiplas interfaces além da API HTTP;
- os testes indiquem acoplamento excessivo entre as camadas;
- a arquitetura atual passe a dificultar a evolução do sistema.

Nesse cenário, arquiteturas como Clean Architecture ou Arquitetura Hexagonal poderão ser consideradas.

## Relação com outras ADRs

Esta decisão complementa as seguintes decisões arquiteturais:

- ADR-001 — Utilização de Python e FastAPI;
- ADR-002 — Utilização de SQLite;
- ADR-003 — Utilização de Monorepo.
