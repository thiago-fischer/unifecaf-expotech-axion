# SPEC-0009 — API do controlador e execução simulada

- Status: API do controlador simulado implementada. Integrações propostas.
- Relacionadas: [ADR-010](../adr/0010-maquete-fisica.md) e [ADR-011](../adr/0011-api-controlador-maquete.md)

## 1. Componentes

| Componente | Responsabilidade |
|---|---|
| Servidor Axion | Gera a OP, coordena os comandos, associa RFID a unidades, registra etapas concluídas e decide o resultado do QA. |
| Controlador simulado | Recebe comandos por HTTP, mantém posições, ocupação e temporizadores, gera leituras RFID simuladas e expõe resultados. |
| Maquete virtual 3D | Exibe o estado e interpola os movimentos. No modo conectado, recebe o estado do controlador simulado. |

O modo demonstrativo atual pode continuar operando com seu motor local.
No modo conectado, o navegador consulta uma rota de leitura exposta pelo
servidor Axion, que repassa o estado da maquete. O controlador simulado mantém
o relógio e a execução mesmo com o navegador fechado.

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
5. Para uma peça aprovada, envia a coleta no QA e o depósito no estoque final. Na primeira simulação, uma reprovação deixa a peça no QA e interrompe o cenário até que o destino de rejeitos seja definido.

## 4. Entregas e validação

1. Implementar a API do controlador simulado e validar o contrato por HTTP.
   Cobrir referência inicial, coleta e depósito, RFID, processamento em
   paralelo, conflito por ocupação e reenvio sem repetir a ação.
2. Executar pelo servidor uma sequência de teste para uma OP, desde o
   armazém até o estoque final. Cobrir também RFID divergente no QA e
   interrupção por perda de estado do controlador.
3. Conectar a cena Three.js ao estado do controlador e verificar posições,
   ocupação, transições e continuidade da execução com a tela fechada.
4. Integrar a programação do otimizador à execução simulada. O planejador
   atual ainda usa um modelo simplificado. O servidor precisa respeitar os
   recursos, a ocupação e os tempos simulados ao transformar o plano em
   comandos. A preparação para hardware depende das restrições descritas na
   [SPEC-0005](0005-production-planning.md#11-pendências-e-evolução-física).

Tempos e leituras usados nesse fluxo são simulados. A validação física
continua pendente, incluindo a perda de comunicação durante o transporte.
