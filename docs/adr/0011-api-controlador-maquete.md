# ADR-011 — API HTTP para o controlador da maquete

- Status: Implementada no controlador simulado; revisão por outro integrante pendente
- Data: 12/11/2026
- Relacionadas: [ADR-010](0010-maquete-fisica.md) e [SPEC-0009](../specs/0009-api-controlador-maquete.md)

## Contexto

O servidor do Axion vai coordenar a execução da ordem de produção (OP).
A maquete física ainda não está disponível. A simulação atual roda no
navegador e decide localmente o próximo movimento, conforme a
[ADR-008](0008-maquete-virtual-threejs.md).

## Proposta

Definir um contrato HTTP/JSON entre o servidor e o controlador central.
Implementar primeiro um controlador simulado como serviço separado, com
API real em FastAPI. O servidor envia comandos e consulta os resultados.
A cena 3D acompanha o estado publicado pelo controlador simulado.

O servidor mantém o plano, a associação entre RFID e unidade da OP, o
histórico e a decisão de QA. O controlador mantém o estado da mesa e das
estações, executa os comandos e verifica se os recursos estão disponíveis.
O simulador pode avançar mesmo com a interface 3D fechada.

## Justificativa

O serviço separado permite testar o mesmo limite de rede previsto para o
hardware. HTTP simplifica o envio e a inspeção dos comandos. Consultas
periódicas atendem ao acompanhamento inicial e permitem recuperar o resultado
de um comando cujo retorno inicial se perdeu.

## Consequências

A API do simulador está disponível no módulo
[`controller`](../../controller/README.md). O
[backend](../../backend/README.md#executar-a-ordem-na-maquete-simulada)
coordena uma OP simulada por vez a partir das filas por máquina.
A adaptação da cena é uma etapa posterior. Quando o controlador físico
estiver disponível, ele poderá implementar o mesmo contrato.
Sensores, tempos reais, comportamento em falhas e regras de recuperação no
hardware precisarão de validação na maquete física.
