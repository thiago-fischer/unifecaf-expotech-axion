# Arquitetura do Axion

> **Versão:** 0.3
>
> **Status:** Em definição
>
> **Última atualização:** 17/10/2026

## Visão Geral

O Axion será desenvolvido utilizando uma arquitetura composta por diferentes componentes integrados, responsáveis pela interface, regras de negócio, otimização, persistência e controle da maquete física.

## Componentes

### Frontend

Responsável pela interface com o usuário.

Implementado em `frontend/` com React, TypeScript e Vite para uso local,
conforme a [SPEC-0006](specs/0006-react-frontend.md) e a
[ADR-007](adr/0007-react-frontend.md). Componentes funcionais e hooks organizam
as áreas de máquinas, produtos, ordens e planejamento. A navegação é em memória,
sem roteador; CSS responsivo atende desktop e telas menores.

O cliente usa `fetch` para `/api`, encaminhado pelo proxy local do Vite à API
configurada por ambiente. Não há acesso direto ao banco, alteração de contratos
HTTP ou necessidade de CORS nesse fluxo. Resultados de planejamento são
transitórios, com nomes do snapshot e distinção entre viabilidade e prova de
ótimo. Um Gantt por máquina apresenta as operações; a tabela detalhada começa
recolhida e permite expansão por mouse ou teclado. Não há execução física.
Veja [comandos e validação](../frontend/README.md).

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
os catálogos de máquinas (SPEC-0001), produtos com etapas (SPEC-0003) e ordens
de produção com produtos e quantidades (SPEC-0004). Produto e etapas, assim como
ordem e itens, são gravados atomicamente. Ordens registram demanda; a rota
separada de planejamento da SPEC-0005 produz resposta transitória sem alterar
o banco. A execução física permanece prevista. Chaves estrangeiras SQLite são
habilitadas em todas as conexões. Consulte o [backend](../backend/README.md)
para instalação, migrations e testes. Os demais componentes continuam planejados.

### Otimização

Responsável pelos algoritmos de Inteligência Computacional utilizados para o planejamento da produção.

**Tecnologia:**

- Python

Implementado em `optimizer/`, pacote Python local `axion_optimizer` 0.1.0,
dependência explícita do backend, independente de HTTP/ORM. O núcleo usa AG
com referências canônica/SPT, decodificação com encaixe em lacunas, elitismo,
OX e swap, seguido por CP-SAT do OR-Tools 9.15.6755 no modelo completo.

A [SPEC-0005](specs/0005-production-planning.md) e a
[ADR-006 proposta](adr/0006-ag-cpsat-production-planning.md) detalham AG
obrigatório com verificação/certificação CP-SAT e contrato de cronograma para
Gantt. A implementação segue a spec aprovada; a ADR-006 permanece **Proposta**,
aguardando revisão da equipe. Veja [instalação e limites](../optimizer/README.md)
e [experimentos](planning-validation.md).

O service carrega o snapshot por repository e fecha a sessão antes da busca.
Uma trava permite uma busca por processo, sem fila; concorrentes recebem 503.
Cada chamada executa AG e certificação, preserva melhorias do solver com autoria
explícita e valida o cronograma independentemente. O contrato padrão responde
409 com candidato quando não há prova de ótimo; `allow_feasible` aceita 200
exploratório. Não há persistência de plano, migration nem execução física.

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
| Frontend | React, TypeScript e Vite |
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

- protocolo de comunicação;
- aceitação formal da ADR-006 para AG/CP-SAT já implementados pela SPEC-0005;
- cloud;
- mecanismo de identificação da matéria-prima.

## ADRs Relacionadas

- ADR-001 — Python e FastAPI
- ADR-002 — SQLite
- ADR-003 — Monorepo
- ADR-004 — Arquitetura em Camadas para o Backend
- [ADR-005 — SQLAlchemy, Pydantic e Alembic](adr/0005-sqlalchemy-pydantic-alembic.md)
- [ADR-007 — Frontend React local](adr/0007-react-frontend.md)

## Maquete virtual

A área Simulação do frontend implementa a SPEC-0007 com Three.js e motor
local determinístico em TypeScript, conforme a [ADR-008](adr/0008-maquete-virtual-threejs.md).
A cena consome estado e interpola movimentos; regras de capacidade e tempo
ficam separadas da renderização. Não há novos endpoints ou persistência.
O cenário demonstrativo é independente do otimizador e não controla hardware.
