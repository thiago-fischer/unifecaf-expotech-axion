# ADR-012 — Captura sanitizada de rede no laboratório

- Status: Aceita
- Data: 14/11/2026

## Contexto

O painel de Telecomunicações precisa demonstrar a comunicação real do ambiente
Docker antes da maquete física. A captura exige capacidades de rede e pode
observar informações sensíveis caso armazene pacotes ou campos livres.

## Decisão

- A captura será opcional e limitada ao profile Compose `network-lab`.
- O coletor compartilhará o namespace do backend e observará somente TCP nas
  portas 8000, 8001 e 5432.
- A imagem usará Debian 12.12 slim pelo digest
  `sha256:d5d3f9c23164ea16f31852f95bd5959aad1c5e854332fe00f7b3a20fcc9f635c`
  e TShark `4.0.17-0+deb12u3`.
- Um lançador mínimo iniciará com `SETUID`, `SETGID` e `SETPCAP`, trocará para o
  UID 10002 e removerá essas três capacidades do conjunto permitido. O coletor
  executará sem root apenas com `NET_ADMIN` e `NET_RAW`, filesystem somente
  leitura e `no-new-privileges`; não terá porta, volume persistente, socket
  Docker nem `privileged: true`.
- O parser usará uma lista fechada de campos. Payloads, SQL, cabeçalhos, tokens,
  query strings e PCAP não sairão do processo de captura.
- Rotas terão query removida e segmentos numéricos ou UUID normalizados para
  `{id}`. Os fluxos dos endpoints internos de ingestão e heartbeat serão
  descartados para impedir recaptura circular.
- O coletor suprimirá a janela curta em que entrega um lote, evitando que as
  gravações dos próprios agregados sejam reclassificadas como novo tráfego.
  Comunicação legítima concorrente a essa janela pode não aparecer no painel.
- A entrega ao backend usará lotes autenticados de até 100 eventos. O par
  `capture_session_id` e `sequence` identificará o cursor após reinícios.
- O backend guardará até 200 eventos em memória, lotes por 24 horas e agregados
  de 10 segundos por 7 dias. Esses valores são configuráveis dentro de limites.
- O Grafana terá `SELECT` somente em `network_metric_samples`. A tabela de lotes
  permanecerá interna ao backend.
- A captura adicional no namespace do PostgreSQL não faz parte do MVP. O
  protocolo da maquete física continua sujeito a ADR própria.

## Consequências

O painel consegue provar tráfego que atravessa o backend e mantém histórico
agregado. A conexão Grafana → PostgreSQL aparece apenas como configurada porque
fica fora do namespace observado. As capacidades de captura aumentam o impacto
do container, mitigado pelo profile opcional e pelos controles descritos.

A validação cobre software e rede Docker local. Ela não comprova comunicação
Wi-Fi, hardware físico, confidencialidade do HTTP ou capacidade de IDS/SIEM.
