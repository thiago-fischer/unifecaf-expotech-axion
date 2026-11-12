# ADR-010 — Capacidade, movimentação e rastreabilidade da maquete física

- Status: Definida pelo responsável do projeto; revisão por outro integrante pendente
- Data: 12/11/2026

## Contexto

O MVP prevê uma linha em escala reduzida que executa ordens de produção
planejadas pelo servidor. A movimentação horizontal por mesa deslizante
acionada por fuso e o processamento simulado por tempo e displays já fazem
parte do escopo.

## Decisão

A maquete física comportará até 10 peças e terá três máquinas de
processamento e uma estação dedicada à revisão de qualidade (QA).
Cada peça será um cubo metálico com uma etiqueta RFID de identificador único.
Um eletroímã fará a captura dos cubos.

1. O servidor gera a ordem de produção (OP), otimiza a programação e envia
   comandos à maquete de acordo com a sequência planejada.
2. A maquete retira um cubo do armazém com o eletroímã e o leva até o leitor
   RFID. O sistema associa o primeiro cubo lido à primeira unidade do produto
   a executar na OP. Para as demais unidades, repete a leitura e a associação
   conforme a sequência planejada.
3. A mesa transporta cada cubo entre as máquinas previstas para seu produto.
   As estações simulam as operações por tempo e displays, sem transformar o cubo.
4. Após o processamento, a peça passa pela estação de QA. A validação confere
   o RFID e o histórico de etapas da unidade. A peça aprovada segue ao estoque
   final.

## Justificativa

A estação dedicada dá um ponto definido para conferir a identidade e o
histórico da peça antes do estoque final. O eletroímã faz a coleta do cubo
metálico, e o RFID vincula a peça física ao item da OP desde a entrada.

## Consequências

O projeto mecânico e a integração com o servidor deverão prever a capacidade
de 10 peças e o percurso entre armazém, leitor, processamento, QA e estoque
final. A execução física permanece planejada e depende de validação em hardware.

Continuam em aberto o mecanismo de elevação, a capacidade das áreas de espera,
os tempos de deslocamento, carga e descarga, as regras de uso da mesa
compartilhada, o protocolo de comunicação e o destino físico de peças reprovadas.
O estudo de planejamento detalha as restrições a incorporar antes da execução.
[SPEC-0005](../specs/0005-production-planning.md#11-pendências-e-evolução-física)
