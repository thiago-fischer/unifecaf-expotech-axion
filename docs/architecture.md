# Arquitetura do Axion

> **Versão:** 0.1  
> **Status:** Em definição  
> **Última atualização:** 15/09/2026

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
| Otimização | Python |
| Observabilidade | Grafana |
| Versionamento | Git / GitHub |
| Organização | Monorepo |

## Tecnologias Ainda em Definição

- frontend;
- protocolo de comunicação;
- algoritmo de otimização;
- biblioteca de otimização;
- ORM;
- cloud;
- mecanismo de identificação da matéria-prima.

## ADRs Relacionadas

- ADR-001 — Python e FastAPI
- ADR-002 — SQLite
- ADR-003 — Monorepo
- ADR-004 — Arquitetura em Camadas para o Backend
