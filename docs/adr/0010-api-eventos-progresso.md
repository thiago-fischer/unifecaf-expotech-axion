# ADR-010 — API HTTP para eventos de progresso do firmware

- Status: Aceita para registrar eventos recebidos; autenticação e execução física não aprovadas
- Data: 26/10/2026
- Relacionada: [SPEC-0008](../specs/0008-firmware-esp32.md),
  [SPEC-0009](../specs/0009-api-progresso-firmware.md) e
  [ADR-005](0005-sqlalchemy-pydantic-alembic.md)

## Contexto

Ordens existentes representam demanda e não possuem estado operacional.
O firmware precisa reportar observações sem alterar silenciosamente as
quantidades solicitadas ou afirmar que uma receita foi validada. O backend
segue FastAPI, arquitetura em camadas, schemas Pydantic separados dos models
SQLAlchemy, SQLite e migrations Alembic.

O ESP32 também terá uma rota local de comando na PoC, mas isso não estabelece
um contrato completo do backend para enviar comandos. Esta decisão é somente
sobre a direção firmware → backend.

## Decisão

- Expor `POST /orders/{order_id}/progress` na API FastAPI para criar eventos
  imutáveis associados à ordem.
- Usar `POST` porque cada alteração de estado é um novo evento; não sobrescrever
  um único estado corrente com `PUT`.
- Exigir `device_id`, `event_id`, `unit_id`, `product_id` e `status`. Aceitar
  opcionalmente `step_sequence`, `message` e `occurred_at` com as regras da
  [SPEC-0009](../specs/0009-api-progresso-firmware.md).
- Aceitar os estados `started`, `in_progress`, `completed` e `failed`. Esses
  valores registram declarações do dispositivo, não validação independente
  da execução.
- Persistir cada evento em `progress_events` através de controller, service,
  repository e model separados, com schema Pydantic de entrada/saída.
- Vincular `(order_id, product_id)` à linha da ordem por chave estrangeira
  composta; rejeitar produto que não pertença à ordem.
- Tornar reenvio idempotente pela restrição única `(device_id, event_id)`.
  Mesmo payload devolve `200` e `duplicate: true`; conteúdo diferente devolve
  `409`. Novo evento devolve `201`.
- Guardar `received_at` UTC do servidor e aceitar `occurred_at` somente com
  fuso informado. A API não depende de relógio sincronizado no microcontrolador.
- Criar estrutura com migration Alembic; não usar `create_all()` na inicialização.

O prefixo `/api` não pertence à rota do FastAPI. O proxy Vite pode apresentar
`/api/orders/{order_id}/progress` ao navegador e remover o prefixo antes de
encaminhar ao backend.

## Justificativa e alternativas

Um log append-only preserva o histórico e permite distinguir início, progresso,
falha e conclusão. `PUT` para sobrescrever o progresso perderia eventos
intermediários ou exigiria um recurso por evento de qualquer maneira.
Idempotência com identificador do dispositivo e evento permite retries após
falha de rede sem duplicar gravações.

O endpoint valida a relação da ordem e do produto, mas evita introduzir uma
máquina de estados de execução antes de existirem unidades físicas persistidas,
receitas versionadas, estratégia de cancelamento e regras de replanejamento.
Estados de evento fora de ordem podem ser armazenados; reconciliá-los é
responsabilidade futura e explicitamente não implementada.

## Segurança e limites aceitos

- A API atualmente não autentica dispositivos. `device_id` é apenas um valor
  declarado e não prova identidade.
- A configuração local padrão escuta em `127.0.0.1`, portanto dispositivos
  externos não alcançam o serviço sem alterar explicitamente a exposição.
- A PoC usa HTTP simples e não deve operar em rede compartilhada. TLS,
  autenticação, autorização, replay window, rate limiting, retenção e
  monitoramento exigem avaliação antes de uso fora de laboratório.
- Payloads não contêm token ou segredo. O contrato não oferece comando remoto.
- Eventos não criam nem associam unidades físicas; o par unit_id/product_id
  ainda não é validado contra registro de rastreabilidade individual.
- A API não inicia, pausa, cancela ou autoriza uma ordem e não atesta que o
  dispositivo executou fisicamente o que declarou.

## Pendências explícitas

- Estratégia de identidade, provisionamento e autenticação por dispositivo.
- Segurança de transporte e exposição controlada da API na rede da maquete.
- Registro de unidades físicas e associação com produto, ordem e receita.
- Regras de transição, ordenação, reconciliação e recuperação de eventos.
- Política de retenção/expurgo e limite de volume do histórico.
- Contrato de comandos backend → ESP32, confirmação, cancelamento e retry.
- Integração do frontend e métricas com o histórico.

Esses temas não são resolvidos pela aceitação desta API de registro e devem ter
decisões próprias antes de implementação ou implantação.

## Consequências

- O backend oferece um contrato documentado e persistente para eventos de
  progresso, testável sem hardware.
- A migration e os testes são necessários para reproduzir o novo contrato.
- O progresso recebido é evidência declarada pelo dispositivo, não prova física
  independente nem autorização de execução.

## Referências

- [SPEC-0004 — Ordens de produção](../specs/0004-production-orders.md).
- [SPEC-0005 — Otimização](../specs/0005-production-planning.md).
- [SPEC-0008 — Firmware ESP32](../specs/0008-firmware-esp32.md).
- [SPEC-0009 — API de eventos de progresso](../specs/0009-api-progresso-firmware.md).
