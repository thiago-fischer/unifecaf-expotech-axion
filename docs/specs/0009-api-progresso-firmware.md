# SPEC-0009 — API de eventos de progresso do firmware

> **Status:** Implementada no backend; revisão por outro integrante e integração
> com dispositivo físico pendentes.
>
> **Data:** 26/10/2026
>
> **Relacionada:** [SPEC-0008](0008-firmware-esp32.md),
> [ADR-009](../adr/0009-firmware-esp32-platformio.md) e
> [ADR-010](../adr/0010-api-eventos-progresso.md).

## 1. Objetivo

Definir o contrato para o firmware reportar ao backend observações de execução
associadas a uma ordem. A API registra eventos imutáveis e idempotentes, sem
alterar a demanda da ordem, criar unidades físicas automaticamente, validar
receitas executadas ou autorizar movimentos na maquete.

Esta entrega completa apenas o canal firmware → backend para eventos de
progresso. A PoC da SPEC-0008 cobre o sentido inverso somente para receber e
imprimir JSON de teste; ela não envia eventos a esta rota.

## 2. Rota

| Método e rota FastAPI | Resposta | Significado |
|---|---:|---|
| `POST /orders/{order_id}/progress` | `201 Created` | Evento novo persistido |
| `POST /orders/{order_id}/progress` | `200 OK` | Reenvio idêntico já registrado |

`order_id` deve ser inteiro positivo e referenciar uma ordem existente. O
FastAPI não adiciona prefixo `/api`; portanto, a URL direta é
`http://<host>:<porta>/orders/{order_id}/progress`. O proxy de desenvolvimento
do frontend remove `/api`, então clientes que o utilizam chamam
`/api/orders/{order_id}/progress`.

### Corpo da requisição

```json
{
  "device_id": "esp32-linha-01",
  "event_id": "evt-001",
  "unit_id": "MAT-001",
  "product_id": 1,
  "status": "in_progress",
  "step_sequence": 1,
  "message": "Etapa iniciada",
  "occurred_at": "2026-10-26T19:00:00-03:00"
}
```

Campos:

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `device_id` | string | Sim | 1–64 caracteres ASCII: letras, números, `.`, `_`, `:`, `-`; começa por letra/número |
| `event_id` | string | Sim | 1–64 caracteres; chave idempotente por dispositivo |
| `unit_id` | string | Sim | 1–128 caracteres; identificador opaco da unidade física |
| `product_id` | inteiro | Sim | Inteiro estrito maior que zero; precisa constar na ordem |
| `status` | enum | Sim | `started`, `in_progress`, `completed` ou `failed` |
| `step_sequence` | inteiro ou `null` | Não | Inteiro estrito maior que zero |
| `message` | string ou `null` | Não | Até 500 caracteres |
| `occurred_at` | data/hora ou `null` | Não | ISO 8601 com fuso horário; normalizado para UTC. Ausente significa que o dispositivo não forneceu relógio confiável |

Campos adicionais são rejeitados. IDs de dispositivo, evento e unidade não
aceitam espaços nem caracteres de controle. O backend valida que o produto
informado é um item da ordem, mas não confirma se a unidade física está
associada a esse produto, se a etapa corresponde à receita ou se a sequência
de eventos é válida.

### Resposta

Resposta de exemplo para evento novo (`201`) ou reenvio idêntico (`200`):

```json
{
  "event": {
    "id": 1,
    "order_id": 12,
    "product_id": 1,
    "device_id": "esp32-linha-01",
    "event_id": "evt-001",
    "unit_id": "MAT-001",
    "status": "in_progress",
    "step_sequence": 1,
    "message": "Etapa iniciada",
    "occurred_at": "2026-10-26T22:00:00Z",
    "received_at": "2026-10-26T22:00:01Z"
  },
  "duplicate": false
}
```

`duplicate` é `true` para o reenvio idêntico e `false` na primeira gravação.
`received_at` é a hora UTC atribuída pelo backend; `occurred_at` é opcional e
representa a hora declarada pelo dispositivo.

## 3. Validação e erros

| Status HTTP | Uso |
|---:|---|
| `201` | Evento novo gravado |
| `200` | Mesmo `device_id` e `event_id`, com conteúdo idêntico |
| `404` | Ordem inexistente |
| `409` | Mesmo `device_id` e `event_id` reapresentado com outro conteúdo |
| `422` | Payload inválido ou `product_id` fora da ordem |
| `500` | Falha inesperada de persistência, com detalhe interno omitido da resposta |

O evento usa uma restrição única em `(device_id, event_id)`. O cliente deve
reutilizar o mesmo `event_id` ao repetir exatamente o mesmo evento após timeout.
Um ID já usado não pode representar um evento diferente. Cada evento novo,
inclusive eventos sucessivos de uma mesma unidade, utiliza um novo `event_id`.

## 4. Persistência e camadas

Eventos são armazenados na tabela `progress_events`, criada pela migration
Alembic `2f63c1a8b4d7`. Uma chave estrangeira composta garante que o par
`(order_id, product_id)` exista em `production_order_items`. A ordem permanece
um registro de demanda; a tabela de eventos não altera a quantidade, o estado
ou os itens da ordem.

O controller trata HTTP, o service valida a regra de associação com a ordem,
o repository persiste e consulta os eventos, o model representa a tabela e o
schema Pydantic define os contratos. Não há escrita direta no banco pelo
controller.

## 5. Segurança e limites

- A API atual não autentica dispositivos. A rota não deve ser exposta a redes
  compartilhadas ou à Internet.
- A configuração padrão do backend escuta em `127.0.0.1`; um dispositivo
  físico não alcança esse endereço em outra máquina. Exposição em rede exige
  configuração de execução explícita, isolamento e autenticação ainda não
  implementada.
- HTTP não criptografado não protege identidade, integridade ou confidencialidade.
- `device_id` identifica o dispositivo no payload, mas não prova sua identidade.
- O contrato não implementa rate limit, expiração de chaves, retenção ou
  compactação do histórico.
- O identificador físico, pareamento unidade-produto, consistência de
  transições e reconciliação de execução são decisões futuras.

## 6. Validação desta entrega

Testes automatizados verificam criação e persistência, reenvio idempotente,
conflito de identificador, associação do produto à ordem, validação de payload,
normalização de data/hora e publicação da rota no OpenAPI. Eles usam banco de
teste com migrations e não comprovam conectividade com ESP32 ou funcionamento
em hardware real.

## 7. Referências

- [SPEC-0004 — Ordens de produção](0004-production-orders.md): ordem representa demanda.
- [SPEC-0005 — Planejamento](0005-production-planning.md): plano atual não é comando físico aprovado.
- [SPEC-0008 — Firmware ESP32](0008-firmware-esp32.md).
- [ADR-005 — SQLAlchemy, Pydantic e Alembic](../adr/0005-sqlalchemy-pydantic-alembic.md).
- [ADR-009 — Plataforma e bibliotecas do firmware](../adr/0009-firmware-esp32-platformio.md).
- [ADR-010 — API de eventos de progresso](../adr/0010-api-eventos-progresso.md).
