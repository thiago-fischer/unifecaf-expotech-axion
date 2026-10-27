# Firmware ESP32

PoC da [SPEC-0008](../docs/specs/0008-firmware-esp32.md), com contrato de
progresso documentado na [SPEC-0009](../docs/specs/0009-api-progresso-firmware.md).
O firmware recebe JSON em `POST /api/firmware/command`, registra a mensagem no
monitor serial e **não aciona motores, sensores nem GPIO**. A rota de comandos
é exclusiva desta PoC e ainda não possui cliente no backend.

## Requisitos

- VS Code com a extensão PlatformIO IDE, ou PlatformIO Core.
- Placa ESP32 compatível com `esp32dev`.
- Credenciais de uma rede Wi-Fi isolada para o protótipo.

As versões da plataforma e das bibliotecas estão fixadas no
[`platformio.ini`](platformio.ini). PlatformIO baixa toolchain e dependências
na primeira compilação; a conectividade é necessária nessa etapa.

## Configuração e execução

1. Copie `include/secrets.h.example` para `include/secrets.h` e preencha SSID e
   senha somente no arquivo local. `secrets.h` é ignorado pelo Git.
2. No terminal dentro de `firmware/`, compile e envie para a placa:

   ```sh
   pio run
   pio run --target upload
   pio device monitor --baud 115200
   ```

   Na extensão, os comandos equivalentes são **Build**, **Upload** e
   **Monitor** na barra de status do PlatformIO.
3. Consulte o IP impresso no monitor serial após a conexão.
4. Envie um objeto JSON de teste a partir de um cliente na mesma rede isolada:

   ```sh
   curl -X POST http://ESP32_IP/api/firmware/command \
     -H 'Content-Type: application/json' \
     -d '{"command_id":"poc-1","command":"noop"}'
   ```

   A resposta esperada é `200` com `{"accepted":true,"hardware_action":"none"}`.
   JSON inválido retorna `400`; corpos maiores que 1024 bytes são rejeitados.
   A mensagem recebida aparece no monitor serial.

Sem `secrets.h`, o projeto ainda compila, mas informa no serial que não há
credenciais e não se conecta ao Wi-Fi.

## Segurança e limites

O servidor HTTP da PoC não implementa autenticação nem criptografia. Use-o
somente em uma rede de laboratório isolada; não o exponha à Internet ou a uma
rede compartilhada. A PoC não movimenta hardware, não informa progresso ao
backend e não valida segurança elétrica ou mecânica. A compilação não substitui
ensaio em placa real.
