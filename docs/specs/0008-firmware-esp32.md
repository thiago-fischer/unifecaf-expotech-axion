# SPEC-0008 — Firmware para controle da maquete com ESP32

> **Status:** Aprovada para PoC; estrutura e recepção de comandos implementadas,
> integração física e validação em hardware pendentes.
>
> **Data:** 26/10/2026
>
> **Origem:** Solicitação de estruturar a camada de firmware para a maquete Axion.

## 1. Objetivo e contexto

Especificar a primeira camada embarcada do Axion, responsável por interagir
com sensores e atuadores da maquete e trocar informações de execução com o
backend. O firmware deverá permitir que comandos operacionais sejam recebidos
sem bloquear a leitura periódica dos sinais físicos e que o progresso das
unidades seja comunicado ao sistema.

O backend e o otimizador já cadastram produtos, ordens e planos em software,
mas não executam ordens físicas. A maquete virtual da [SPEC-0007](0007-maquete-virtual.md)
é uma demonstração local independente, não controla o hardware e não valida
este firmware. Esta SPEC não autoriza executar fisicamente um plano da
[SPEC-0005](0005-production-planning.md).

## 2. Decisões aprovadas para a PoC

Como ponto de partida para avaliação, propõe-se:

- perfil PlatformIO `esp32dev`, framework Arduino;
- `ESPAsyncWebServer` para receber requisições HTTP sem bloquear futuras
  tarefas periódicas do dispositivo;
- `ArduinoJson` para validar e decodificar JSON;
- projeto em `firmware/`, com código em `firmware/src/` e cabeçalhos em
  `firmware/include/`;
- `firmware/.pio/` ignorado pelo Git.

As versões fixadas e a decisão estão registradas na
[ADR-009](../adr/0009-firmware-esp32-platformio.md). `esp32dev` é um perfil
de compilação; o fabricante e a revisão exatos da placa ainda não foram
confirmados em hardware.

## 3. Escopo

### Implementado nesta entrega

- Projeto PlatformIO compilável para a configuração `esp32dev`.
- Tentativa de conexão Wi-Fi sem credenciais versionadas; sem `secrets.h`,
  compila desconectado e informa a ausência de configuração pelo serial.
- Servidor HTTP na porta 80, rota `POST /api/firmware/command`, limite de corpo
  de 1024 bytes e validação de objeto JSON.
- Impressão do JSON recebido no monitor serial e resposta explícita
  `hardware_action: none`.
- Documentação de instalação, build, upload, monitor serial e limites na
  [pasta firmware](../../firmware/README.md).

### Fora desta PoC

- Leitura de sensores, acionamento de GPIO, motores ou displays.
- Envio de progresso do ESP32 ao backend.
- Cliente backend para envio de comandos ao ESP32.
- Autenticação, TLS e implantação em rede compartilhada.
- Validação em placa, sensores, atuadores ou maquete reais.

### Fora do escopo desta proposta

- Definição mecânica ou elétrica de motores, sensores, drivers, fontes,
  pinagem, limites de curso ou paradas de emergência.
- Alteração da lógica de cadastro, persistência ou otimização do backend.
- Garantia de ótimo ou autorização para executar um plano físico.
- Identificação física definitiva das unidades e validação de qualidade real.
- Transformação física de matéria-prima; o processamento segue simulado por
  tempo e displays no escopo do MVP.
- Cloud, OTA, dashboards ou escolha de mecanismos de segurança de rede.

O transporte horizontal por mesa deslizante acionada por fuso segue o escopo
geral do projeto. A SPEC não escolhe motores, drivers, sensores de posição nem
outras soluções mecânicas ainda em estudo.

## 4. Responsabilidades e integração

O firmware deverá concentrar o controle de baixo nível dos sinais e atuadores.
O backend continuará responsável pelas regras de negócio, estado persistido,
identidade e histórico das unidades e coordenação das operações. O firmware
não acessará diretamente o banco de dados nem será responsável por recalcular
o cronograma de produção.

A integração deverá permitir, conceitualmente:

1. o backend enviar um comando direcionado a um dispositivo;
2. o dispositivo validar e confirmar o recebimento ou rejeitar o comando;
3. o dispositivo observar a execução local e reportar progresso, conclusão
   ou falha;
4. o backend validar e registrar esses eventos segundo regras a definir.

O endpoint local `POST /api/firmware/command` recebe JSON de teste; seu
contrato ainda não representa comandos de produção nem possui remetente no
backend. Para o fluxo inverso, a API implementa
`POST /orders/{order_id}/progress`, definido na
[SPEC-0009](0009-api-progresso-firmware.md), para persistir eventos declarados
por dispositivos. A PoC não chama essa rota.

## 5. Requisitos funcionais propostos

- **RF-01:** O dispositivo deve iniciar suas saídas em estado seguro, sem
  movimento não solicitado durante inicialização ou reconexão.
- **RF-02:** O dispositivo deve conectar-se à rede configurada sem armazenar
  credenciais reais no repositório. A configuração e tentativa de conexão estão
  implementadas; a conexão física depende de credenciais locais e placa.
- **RF-03:** O dispositivo deve receber comandos sem manter a leitura de
  sensores e o controle local bloqueados durante operações demoradas. A PoC
  usa servidor assíncrono, mas ainda não possui leitura de sensores.
- **RF-04:** Cada comando deve ser validado antes de produzir qualquer efeito
  físico; comandos inválidos ou incompatíveis com o estado atual devem ser
  rejeitados explicitamente.
- **RF-05:** A leitura dos sensores deve ocorrer de forma periódica, com
  intervalo configurável após a definição dos componentes e requisitos de
  resposta.
- **RF-06:** Mudanças de estado relevantes devem ser reportadas ao backend com
  referência ao dispositivo e ao comando ou unidade relacionados, quando
  disponíveis.
- **RF-07:** Falhas ou perda de comunicação não devem resultar em confirmação
  falsa de conclusão. O dispositivo deve manter um estado local seguro e
  permitir reconciliação após a reconexão.
- **RF-08:** A entrega deverá distinguir mensagens aceitas, rejeitadas e
  estados físicos observados; recebimento de comando não equivale à conclusão
  da operação.

## 6. Requisitos não funcionais e segurança

- O ciclo de controle não deve depender de espera bloqueante por rede ou por
  duração de processamento.
- Credenciais Wi-Fi e quaisquer segredos devem vir de configuração local não
  versionada; arquivos de exemplo não devem conter credenciais válidas.
- O firmware deve limitar e validar o conteúdo recebido antes de processar
  JSON, incluindo tamanho e tipos dos campos, conforme limites a definir.
- Comandos desconhecidos, malformados ou inconsistentes devem gerar resposta
  explícita e não devem acionar GPIO.
- A exposição do servidor do ESP32, autenticação, autorização, proteção contra
  repetição de comandos e segmentação de rede precisam ser avaliadas antes de
  conectar o dispositivo a uma rede compartilhada.
- HTTP sem proteção criptográfica não deve ser tratado como seguro fora de uma
  rede isolada e controlada; a escolha de transporte e mitigação precisa de
  decisão arquitetural e validação prática.
- Acionamentos e falhas devem ser observáveis por logs de diagnóstico sem
  registrar segredos.

## 7. Organização implementada

```text
firmware/
├── include/
├── src/
│   └── main.cpp
└── platformio.ini
```

O `main.cpp` inicializa Wi-Fi e servidor. O `loop()` acompanha o estado da
conexão sem executar leitura de sensores ou acionar saídas. O código de
hardware permanece fora da PoC até definição elétrica e mecânica.

`.gitignore` ignora `firmware/.pio/` e `firmware/include/secrets.h`.

## 8. Critérios e situação da validação

- `pio run` compilou com sucesso para `esp32dev`; o relatório indicou 8,7% de
  RAM e 40,8% de flash usados. A compilação foi feita sem placa conectada.
- O código da PoC não contém acionamento de GPIO, motores ou sensores.
- O código responde com erro para JSON inválido e corpos acima do limite; o
  comportamento HTTP ainda precisa ser exercitado com a placa em rede.
- A conexão Wi-Fi exige credenciais locais e teste em placa; não se presume
  sucesso a partir da compilação.
- A API de progresso possui testes automatizados no backend, mas ainda não foi
  chamada por um ESP32.
- Ensaios físicos devem documentar placa, componentes, pinagem, cenário,
  resultados e limitações. Compilação e simulação de mensagens não comprovam
  operação física segura ou correta.

## 9. Decisões pendentes

- Fabricante e revisão exatos da placa, hardware elétrico e validação física.
- Topologia de rede para operação e exposição controlada da API.
- Autenticação por dispositivo, TLS, provisionamento e rotação de chaves.
- Contrato de comandos backend → ESP32; a rota da PoC não está integrada.
- Mapeamento GPIO, componentes elétricos, intertravamentos e estados seguros.
- Frequência de amostragem, timeout, estratégia de reconexão e persistência
  local temporária de eventos.
- Associação física segura entre dispositivo, ordem, unidade e produto.
- Critérios para parada, retomada, cancelamento e recuperação após reinício.

As decisões de tecnologia da PoC não aprovam essas escolhas pendentes. Novas
decisões arquiteturais devem ser justificadas e registradas em ADR antes da
implementação correspondente.

## 10. Referências

- [Visão geral do Axion](../visao-geral.md): escopo do MVP, maquete e decisões
  ainda em aberto.
- [Arquitetura](../architecture.md): responsabilidades dos componentes e
  estado da integração.
- [ADR-009 — ESP32, PlatformIO e bibliotecas](../adr/0009-firmware-esp32-platformio.md).
- [SPEC-0009 — API de eventos de progresso](0009-api-progresso-firmware.md).
- [ADR-010 — API de eventos de progresso](../adr/0010-api-eventos-progresso.md).
- [SPEC-0001 — Máquinas](0001-backend-machines.md): catálogo de máquinas e
  limites relativos ao controle físico.
- [SPEC-0003 — Produtos e etapas](0003-backend-products.md).
- [SPEC-0004 — Ordens de produção](0004-production-orders.md): ordens não
  iniciam execução física.
- [SPEC-0005 — Otimização e cronograma](0005-production-planning.md): plano
  atual não está autorizado para execução física.
- [SPEC-0007 — Maquete virtual](0007-maquete-virtual.md): demonstração local
  sem integração com hardware.
