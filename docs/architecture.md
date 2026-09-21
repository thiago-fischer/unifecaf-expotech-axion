# Arquitetura do Axion

> **Versão:** 0.2
>
> **Status:** Em definição
>
> **Última atualização:** 21/09/2026

## Visão Geral

O Axion será desenvolvido utilizando uma arquitetura composta por diferentes componentes integrados, responsáveis pela interface, regras de negócio, otimização, persistência e controle da maquete física.

## Componentes

### Frontend

Responsável pela interface com o usuário.

Tecnologia ainda não definida.

### Backend

Responsável pelas regras de negócio e integração entre os componentes.

**Tecnologias:**

- Python
- FastAPI
- Pydantic para validação dos schemas de entrada e saída

**Arquitetura interna:**

```text
Controller
    ↓
Service
    ↓
Repository
    ↓
Model
```

### Persistência

**Banco de dados:**

- SQLite

Utilizado inicialmente devido à simplicidade do projeto e à baixa necessidade de concorrência.

**ORM:** SQLAlchemy 2.x, com acesso síncrono no MVP.

**Migrations:** Alembic, com revisões versionadas desde a criação das primeiras tabelas.

Os models SQLAlchemy serão separados dos schemas Pydantic. Repositories
concentrarão o acesso aos dados; services coordenarão a transação completa
da operação, sem commits independentes nos repositories. Cada requisição
que acessar o banco utilizará uma sessão própria.

A estrutura do banco será preparada e atualizada explicitamente por migrations,
sem `create_all()` na inicialização da API. Essas definições estão registradas
na [ADR-005](adr/0005-sqlalchemy-pydantic-alembic.md) e estão implementadas para
o catálogo de máquinas da SPEC-0001. Consulte o [backend](../backend/README.md)
para instalação, migrations e testes. Os demais componentes continuam planejados.

### Otimização

Responsável pelos algoritmos de Inteligência Computacional utilizados para o planejamento da produção.

**Tecnologia:**

- Python

O algoritmo ainda não foi definido.

### Dispositivos Embarcados

Responsáveis pelo controle da maquete, sensores, motores e displays.

**Tecnologias previstas:**

- ESP32
- Arduino ou equivalente

O protocolo de comunicação ainda não foi definido.

### Observabilidade

**Tecnologia prevista:**

- Grafana

Responsável pela visualização das métricas do processo produtivo.

## Organização do Repositório

O projeto utilizará monorepo.

Estrutura inicial:

```text
axion/
├── backend/
├── frontend/
├── optimizer/
├── firmware/
├── infrastructure/
└── docs/
```

## Tecnologias Definidas

| Área | Tecnologia |
|---|---|
| Backend | Python |
| Framework Backend | FastAPI |
| Banco de Dados | SQLite |
| ORM | SQLAlchemy 2.x, síncrono |
| Schemas da API | Pydantic |
| Migrations | Alembic |
| Otimização | Python |
| Observabilidade | Grafana |
| Versionamento | Git / GitHub |
| Organização | Monorepo |

## Tecnologias Ainda em Definição

- frontend;
- protocolo de comunicação;
- algoritmo de otimização;
- biblioteca de otimização;
- cloud;
- mecanismo de identificação da matéria-prima.

## ADRs Relacionadas

- ADR-001 — Python e FastAPI
- ADR-002 — SQLite
- ADR-003 — Monorepo
- ADR-004 — Arquitetura em Camadas para o Backend
- [ADR-005 — SQLAlchemy, Pydantic e Alembic](adr/0005-sqlalchemy-pydantic-alembic.md)
