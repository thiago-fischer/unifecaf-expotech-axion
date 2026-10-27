# ADR-009 — ESP32, PlatformIO e servidor assíncrono para a PoC de firmware

- Status: Aceita para a PoC e a primeira implementação do firmware; validação em hardware e revisão do PR pendentes
- Data: 26/10/2026
- Relacionada: [SPEC-0008](../specs/0008-firmware-esp32.md) e
  [SPEC-0009](../specs/0009-api-progresso-firmware.md)

## Contexto

O Axion precisa iniciar a camada embarcada separadamente do backend, com um
ambiente reproduzível e uma prova de conceito que receba JSON sem bloquear
futuras tarefas de leitura dos sensores. O firmware deve permanecer isolado em
`firmware/` no monorepo. O hardware final, os sensores, os atuadores e a
pinagem ainda não foram definidos.

## Decisão

- Usar um módulo ESP32 compatível com a definição PlatformIO `esp32dev` para a
  PoC; o fabricante e a revisão exatos da placa ainda serão registrados após
  a aquisição e o teste do hardware.
- Usar PlatformIO Core/IDE e framework Arduino, com `platformio.ini` versionado.
- Fixar nesta implementação:
  - plataforma `espressif32@8.0.0`;
  - `ESP32Async/ESPAsyncWebServer@3.12.1`;
  - dependência explícita `ESP32Async/AsyncTCP@3.5.0`;
  - `bblanchon/ArduinoJson@7.4.3`.
- Executar a PoC como servidor HTTP assíncrono na porta 80, recebendo
  `POST /api/firmware/command`. Limitar o corpo a 1024 bytes, aceitar somente
  um objeto JSON, registrar o conteúdo no monitor serial e responder com
  confirmação que declara `hardware_action: none`.
- Não configurar GPIO, motores ou sensores nesta PoC.
- Manter credenciais Wi-Fi em `firmware/include/secrets.h`, ignorado pelo Git;
  versionar apenas `secrets.h.example` sem valores válidos.
- Ignorar os artefatos PlatformIO em `firmware/.pio/`.

As versões são fixadas para compilação reprodutível desta PoC. Atualizações
exigem recompilação e revisão das notas de versão/compatibilidade; uma versão
fixada não implica que a dependência esteja livre de defeitos.

## Justificativa e alternativas

PlatformIO fornece ambientes por placa e dependências explícitas, integrando
compilação e upload ao VS Code. O framework Arduino reduz o custo inicial para
Wi-Fi e GPIO neste protótipo. `ESPAsyncWebServer` evita que o tratamento da
requisição HTTP monopolize o `loop()` quando a leitura periódica dos sensores
for incorporada. ArduinoJson oferece validação e serialização do corpo JSON.

Uma API HTTP síncrona poderia bloquear a execução do firmware durante o
tratamento de uma requisição; isso é indesejável para futuras leituras de
sensores. ESP-IDF puro permanece uma alternativa se surgirem requisitos que
justifiquem seu custo adicional. A placa `esp32dev` é um perfil de compilação,
não uma especificação elétrica ou mecânica.

## Segurança e limites

- O endpoint da PoC não autentica chamadas, não usa TLS e aceita pedidos de
  qualquer cliente que alcance o dispositivo. Deve permanecer em rede de
  laboratório isolada e nunca ser exposto à Internet.
- A mensagem recebida não aciona hardware e não é encaminhada ao backend.
- Wi-Fi com credenciais vazias deixa o firmware compilável, mas desconectado.
- A rota HTTP de comando é exclusiva da PoC; backend, método de envio, schema
  de comando, autenticação e política de repetição ainda não estão integrados.
- A ligação de motores e sensores exige projeto elétrico, estados seguros,
  proteção, intertravamentos e validação física antes de qualquer controle.

## Pendências explícitas

Não são decisões aceitas por esta ADR:

- fabricante/modelo/revisão final da placa e escolha entre variantes do ESP32;
- topologia de rede, endereçamento, direção definitiva de comando e telemetria;
- autenticação por dispositivo, armazenamento/rotação de chaves e TLS;
- hardware, pinagem, drivers, fontes, limites de curso, sensores e parada de emergência;
- frequências de amostragem, timeouts, estados seguros e comportamento de falha;
- atualização remota, provisionamento e observabilidade em produção.

Estas escolhas devem ser registradas em decisão própria quando forem necessárias.
O uso de Wi-Fi/HTTP nesta PoC não as resolve implicitamente.

## Consequências

- `firmware/` pode ser compilado e receber JSON de teste sem motores ou sensores.
- A PoC não prova estabilidade, latência ou segurança em rede e hardware reais.
- O servidor não deve ser tratado como serviço confiável fora da rede isolada.
- A integração de comando e progresso permanece separada: o contrato de
  progresso backend ← firmware está na ADR-010 e SPEC-0009.

## Referências

- [ESPAsyncWebServer no PlatformIO Registry](https://registry.platformio.org/libraries/ESP32Async/ESPAsyncWebServer).
- [AsyncTCP no PlatformIO Registry](https://registry.platformio.org/libraries/ESP32Async/AsyncTCP).
- [ArduinoJson no PlatformIO Registry](https://registry.platformio.org/libraries/bblanchon/ArduinoJson).
- [Plataforma Espressif32 no PlatformIO Registry](https://registry.platformio.org/platforms/platformio/espressif32).
