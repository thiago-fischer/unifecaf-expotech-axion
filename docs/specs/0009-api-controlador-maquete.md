# SPEC-0009 — API do controlador e execução simulada

- Status: Controlador simulado, coordenador e modo 3D conectado implementados.
- Relacionadas: [ADR-010](../adr/0010-maquete-fisica.md) e [ADR-011](../adr/0011-api-controlador-maquete.md)

## 1. Componentes

| Componente | Responsabilidade |
|---|---|
| Servidor Axion | Gera a OP, coordena os comandos, associa RFID a unidades, registra etapas concluídas e decide o resultado do QA. |
| Controlador simulado | Recebe comandos por HTTP, mantém posições, ocupação e temporizadores, gera leituras RFID simuladas e expõe resultados. |
| Maquete virtual 3D | Exibe o estado e interpola os movimentos. No modo conectado, recebe o estado do controlador simulado. |

O modo demonstrativo atual pode continuar operando com seu motor local.
No modo conectado, o navegador consulta `GET /simulation/status` no
servidor Axion. A resposta combina a última execução com a posição da mesa,
a ocupação por RFID, a leitura atual, os resultados do QA e o estado das
máquinas. O controlador simulado mantém
o relógio e a execução mesmo com o navegador fechado.

### Eventos HTTP e recuperação

O controlador publica `POST /controller/events` ao iniciar ou concluir
comandos e quando muda a sessão, a velocidade ou a leitura RFID.
O corpo contém `status`, com sessão e sequência crescente do snapshot, e
`resultados`, com os comandos concluídos ou que falharam. O backend confirma
com `204`. O simulador tenta reenviar resultados pendentes em caso de falha
na entrega. O backend preserva o snapshot mais recente da sessão e usa o ID
do comando para correlacionar a conclusão.

As abas leem o mesmo estado no backend. O backend consulta o controlador
para obter o estado inicial, recuperar um snapshot com 10 s de idade ou
consultar um comando sem confirmação após 2 s. A cena usa a duração da
trajetória e a idade do snapshot para animar o deslocamento entre eventos.
O Compose configura `AXION_CONTROLLER_EVENTS_URL` e permite definir o
mesmo `AXION_CONTROLLER_EVENTS_TOKEN` nos dois serviços.

O backend repassa o ajuste de velocidade de `POST /simulation/speed` para
`POST /api/simulacao/velocidade` no controlador. O campo `velocidade` aceita
0,5×, 1×, 2× e 4× e aparece no status. A mudança preserva o progresso
dos comandos e ajusta o tempo real de movimento, RFID e processamento.
Restaurar o cenário volta o relógio para 1×.
Nesse ritmo, a mesa leva 0,42 s por intervalo entre posições e a coleta
ou o depósito acrescenta 0,85 s de manipulação. O processamento conserva a
duração informada na receita.

## 2. Contrato HTTP proposto

| Método e rota no controlador | Uso |
|---|---|
| `POST /api/comandos` | Envia um comando identificado pelo servidor. Retorna `202 Accepted` para um novo comando admitido. |
| `GET /api/comandos/{id}` | Retorna o estado do comando, com resultado ou motivo de falha quando houver. |
| `GET /api/status` | Retorna o identificador da sessão do controlador, posição e movimento da mesa, estado do cabeçote, ocupação, estado das estações e falhas. |
| `GET /api/maquinas/{id}/status` | Retorna o estado da estação e, durante o processamento, o tempo restante. |

Os estados do comando são `aceito`, `em_execucao`, `concluido` e `falhou`.
O servidor só libera comandos dependentes após confirmar a conclusão do
comando anterior. Enquanto isso, pode enviar comandos que usem recursos
independentes. Comandos de movimentação e manipulação compartilham a mesa,
e estações diferentes podem processar em paralelo.

O servidor gera um ID por comando e reutiliza o mesmo ID e conteúdo se
precisar repetir o envio. Para um ID já admitido, o controlador devolve
`200 OK` com o estado registrado, sem repetir a operação. O mesmo ID com
conteúdo diferente retorna `409 Conflict`. Um comando incompatível com o
estado atual, como coletar com o cabeçote ocupado, também retorna `409`,
com código de erro que distingue a causa. Uma consulta por ID desconhecido
retorna `404 Not Found`. Na primeira implementação simulada, o registro
pode ficar em memória durante a execução do serviço. O servidor acompanha
o identificador da sessão do controlador. Se esse identificador mudar
durante a OP, o servidor interrompe a execução para reconciliar o estado
antes de reenviar comandos de movimentação.

### Comandos principais

| Tipo | Parâmetros | Resultado e condições |
|---|---|---|
| `referenciar_mesa` | Nenhum | Estabelece a posição inicial antes da primeira movimentação. Exige mesa sem peça e cabeçote recolhido. |
| `mover_para` | `destino` | Move a mesa para uma posição conhecida com o cabeçote recolhido. Pode transportar um cubo. |
| `coletar_peca` | `origem` | Posiciona a mesa, baixa o cabeçote, aciona o eletroímã e recolhe o cubo. Exige origem com peça disponível para retirada e cabeçote vazio. |
| `depositar_peca` | `destino` | Posiciona a mesa, baixa o cubo, desliga o eletroímã e recolhe o cabeçote. Exige cubo no cabeçote e destino livre. |
| `ler_rfid` | `ponto` | Retorna o RFID da peça presente no ponto de entrada ou de QA. A disposição dos leitores físicos permanece em aberto. |
| `iniciar_processamento` | `maquina_id`, `duracao_ms` | Inicia o temporizador de uma estação com peça depositada e pronta para processar. O comando conclui ao fim da operação, e a estação aguarda a retirada. |

As posições são nomes cadastrados no controlador, como `ARMAZEM_01`,
`LEITOR_RFID`, `M1`, `M2`, `M3`, `QA` e `ESTOQUE_FINAL_01`.
A capacidade de referência da simulação conectada segue a ADR-010, com até
10 cubos, três máquinas de processamento e uma estação de QA.

O cenário inicial do serviço contém um cubo por padrão e aceita uma
quantidade configurável de 0 a 10. As leituras devolvem `resultado.rfid`.
O leitor de entrada lê o cubo no cabeçote quando a mesa está no ponto
`LEITOR_RFID`. A leitura de QA usa o cubo depositado naquela estação.
Os tempos de movimentação são valores simulados. O estado `falhou` faz
parte do contrato para falhas durante a execução. O simulador atual
valida as condições antes da admissão e não injeta falhas em comandos aceitos.
Os comandos de instalação e o roteiro HTTP estão no
[README do controlador](../../controller/README.md).

Exemplo de envio para `POST /api/comandos`.

```json
{
  "id": "OP-42-001",
  "tipo": "coletar_peca",
  "parametros": {
    "origem": "ARMAZEM_01"
  }
}
```

Exemplo de resposta `202 Accepted`.

```json
{
  "id": "OP-42-001",
  "estado": "aceito"
}
```

## 3. Fluxo de uma peça

1. No início da execução, o servidor referencia a mesa se necessário. Para cada unidade, manda coletar um cubo no armazém e levá-lo ao ponto de leitura.
2. O controlador retorna o RFID. O servidor associa a leitura à próxima unidade prevista na OP.
3. O servidor ordena o depósito na máquina da primeira etapa e inicia o processamento. Quando a operação termina, coleta o cubo e repete o ciclo nas demais etapas do produto.
4. O servidor manda depositar a peça no QA e solicita a leitura final. Com o RFID e o histórico de etapas, decide se a peça foi aprovada.
5. Peças aprovadas e rejeitadas seguem à mesma esteira de saída. O depósito leva `resultado_qa`, e o servidor registra a divergência de RFID em `rejected_units` sem interromper o restante da OP.

`coletar_peca` em `ARMAZEM` retira o primeiro cubo disponível. Depositar
em `ESTOQUE_FINAL` ocupa a próxima vaga. Cada esteira tem um único ponto
no eixo da mesa e dez posições lógicas. Os endereços numerados continuam
disponíveis para comandos manuais e representam vagas lógicas.

## 4. Filas por máquina no servidor

O servidor agrupa as operações do plano por `machine_id` e ordena cada fila
por `start_seconds`. Cada entrada representa uma operação de uma unidade
específica da OP e mantém `operation_id`, `unit_id`, `step_sequence`,
`predecessor_operation_id` e a duração planejada. O backend disponibiliza a
prévia em `POST /orders/{order_id}/plan/queues`. As filas são derivadas em
memória no servidor.

Para despachar, o coordenador aguarda a predecessora da
primeira operação de cada fila e confere a ocupação real das estações.
Concluir o processamento deixa a máquina aguardando retirada. O coordenador
reserva um destino livre antes de coletar e serializa os comandos
que ocupam a mesa. Peças com a última etapa concluída ficam elegíveis para QA.
Se nenhuma operação estiver pronta para receber uma peça, o coordenador
pode liberar uma estação com operação concluída usando `B1` ou `B2`.
Se houver trabalho pendente e nenhum movimento viável, a execução informa
o bloqueio. O coordenador dá preferência a peças já em circulação e usa
o horário planejado como prioridade entre operações elegíveis.

O operador inicia a execução simulada com
`POST /orders/{order_id}/executions` e fornece o mapeamento do catálogo
para `M1`, `M2` e `M3`. O progresso fica em memória e pode ser consultado
por `GET /orders/{order_id}/executions/{execution_id}`. O plano atual
mantém `execution_ready: false` para execução física. O coordenador usa
a ordem por máquina e decide o momento de cada comando com base na
ocupação e na conclusão das dependências.

O backend envia `X-Axion-Session` ao criar comandos. Se o controlador tiver
reiniciado, o POST retorna `409` com código `sessao_alterada`.
`iniciar_processamento` aceita `continuar_na_maquina: true` para uma nova
etapa do mesmo cubo sem deslocamento, quando a operação anterior terminou.
Comandos manuais no controlador devem ser executados entre OPs.

## 5. Entregas e validação

1. Implementar a API do controlador simulado e validar o contrato por HTTP.
   Cobrir referência inicial, coleta e depósito, RFID, processamento em
   paralelo, conflito por ocupação e reenvio sem repetir a ação.
2. Executar pelo servidor uma sequência de teste para uma OP, desde o
   armazém até o estoque final. Cobrir também RFID divergente no QA e
   interrupção por perda de estado do controlador.
3. Conectar a cena Three.js ao estado do controlador e verificar posições,
   ocupação, transições e continuidade da execução com a tela fechada.
4. Validar a integração da programação do otimizador à execução simulada.
   O coordenador aplica as restrições de ocupação e transporte ao despachar.
   A preparação para hardware depende das restrições descritas na
   [SPEC-0005](0005-production-planning.md#11-pendências-e-evolução-física).

Tempos e leituras usados nesse fluxo são simulados. A validação física
continua pendente, incluindo a perda de comunicação durante o transporte.
