# SPEC-0007 — Maquete virtual 3D e simulação animada da produção

> **Status:** Implementada mediante autorização do responsável; validação local registrada abaixo, revisão de outro integrante pendente.
>
> **Data:** 20/10/2026
>
> **Origem:** Solicitação do responsável para especificar uma simulação com
> acabamento visual inspirado no vídeo apresentado, máquinas, almoxarifado,
> estoque auxiliar e movimentação individual de materiais.

## 1. Objetivo e contexto

Criar uma maquete virtual interativa dentro do frontend do Axion, com volume,
iluminação, sombras e movimentos suaves. Mostrar de forma compreensível o
percurso de cada unidade: saída do almoxarifado, transporte, processamento,
espera entre etapas, validação e armazenamento final.

A referência visual é o arquivo `WhatsApp Video 2026-10-19 at 1.32.50 PM.mp4`,
apresentado pelo responsável em 19/10/2026. Os quadros analisados mostram uma
animação de ordenação com blocos identificados, pórtico, captura vertical,
fundo escuro e perspectiva tridimensional. O vídeo orienta acabamento e
movimento; seu algoritmo de ordenação, textos e marca não são requisitos do
Axion. Não é necessário distribuir o vídeo no repositório.

O responsável esclareceu que o planejador atual é um rascunho e que suas
limitações não devem impedir a criação da animação. A primeira entrega deve
funcionar com um cenário demonstrativo próprio, sem depender de mudanças no
otimizador ou de conexão com hardware.

O frontend React, TypeScript e Vite já existe, conforme a SPEC-0006 e a
ADR-007 aceita. Embora o AGENTS.md ainda liste a escolha de frontend como
aberta, esta spec segue a ADR-007 e a implementação existente. A ADR-006
continua proposta; esta spec não altera o status das decisões de otimização.

## 2. Escopo da primeira entrega

### Incluído

- Nova área **Simulação** no frontend existente, em português.
- Cena 3D com aparência própria do Axion e layout inicial fixo.
- Almoxarifado, três máquinas demonstrativas, estoque auxiliar, transportador,
  estação de validação e áreas de saída e de unidades rejeitadas.
- Unidades com identidade individual, cor por produto e receita ordenada.
- Cenário local determinístico que demonstra máquinas trabalhando em paralelo,
  espera entre etapas e utilização do estoque auxiliar.
- Regras de execução com capacidade finita e tempos de transporte explícitos.
- Controles de reprodução, seleção de unidades e histórico de eventos.
- Indicadores da execução simulada e alternativa textual acessível.

### Fora desta entrega

- Integração obrigatória com ordens reais ou resultados do planejador.
- Alteração do AG/CP-SAT, novas garantias de ótimo ou replanejamento automático.
- Controle de motores, sensores, firmware, protocolos ou leitura física de IDs.
- Simulação de forças, colisões físicas, tolerâncias mecânicas ou projeto CAD.
- Transformação física de materiais e interrupção de operações em andamento.
- Editor de layout, modelos industriais detalhados, cloud, Grafana e multiplayer.
- Persistência de sessões, novos endpoints, tabelas ou migrations.

A tela deve identificar o cenário como **Demonstração simulada**. Identidades,
receitas, estoques e resultados locais não representam registros físicos reais.

## 3. Composição da maquete

| Elemento | Representação e função |
|---|---|
| Base | Plataforma industrial com posições demarcadas, rótulos e estrutura de suporte |
| Almoxarifado | Posições visíveis ocupadas pelas unidades iniciais e contador de saldo |
| Máquinas M1, M2 e M3 | Estações distintas, cada uma com uma posição de processamento e display de produto, etapa e tempo restante |
| Estoque auxiliar | Duas vagas visíveis e identificadas para espera entre operações |
| Transportador | Mesa deslizante com fuso visível, um único conjunto móvel e capacidade de uma unidade |
| Captura vertical | Cabeçote conceitual com animação de aproximação, coleta, elevação e descarga |
| Validação | Uma posição para conferir identidade e histórico esperado da unidade |
| Saída | Posições para unidades aprovadas e contador de produtos concluídos |
| Rejeitados | Área separada para unidades que falhem na validação simulada |

Três máquinas e duas vagas são parâmetros do cenário demonstrativo, não uma
decisão sobre a quantidade definitiva de componentes da maquete física.
Almoxarifado, saída e rejeitados devem comportar todas as unidades do cenário.

Todas as posições de coleta/entrega devem estar ao alcance do mecanismo
representado. O layout inicial deve alinhar essas posições ao eixo horizontal;
não mostrar movimentos laterais que exigiriam um eixo ausente da cena.

O transporte horizontal por fuso segue o escopo do projeto. Movimento vertical
e captura continuam em estudo: a aparência do cabeçote é ilustrativa, sem
aprovar garra, eletroímã ou mecanismo definitivo de construção.

## 4. Direção visual e animação

- Câmera inicial em perspectiva de três quartos, enquadrando toda a maquete.
- Fundo escuro, materiais industriais, contraste entre base, máquinas e peças,
  iluminação direcionada e sombras que evidenciem contato e profundidade.
- Geometrias com espessura e bordas trabalhadas; evitar aparência de caixas
  planas sem materiais, iluminação ou acabamento.
- Cores consistentes por produto, acompanhadas de IDs e textos; estado nunca
  comunicado somente por cor.
- Displays legíveis e indicadores discretos de máquina ativa, livre ou bloqueada.
- Aproximação e parada suaves do transportador. Coleta e descarga devem ter
  fases visíveis, sem teletransporte ou atravessamento das estações.
- A unidade acompanha o cabeçote somente após a coleta e permanece no destino
  após a descarga; o processamento começa depois da entrega completa.
- Fuso e conjunto móvel devem apresentar movimento coerente entre si, sem
  exigir dimensionamento mecânico real nesta entrega.
- Permitir ajustar a câmera por órbita limitada e zoom, com ação para restaurar
  o enquadramento inicial. Impedir atravessar a base ou perder a maquete de vista.

O acabamento visual é parte do aceite. Uma tabela de estados ou um diagrama
estático, isoladamente, não satisfaz esta spec. Os modelos podem ser criados
com geometrias próprias; assets externos exigem licença compatível e atribuição.

## 5. Regras de execução simulada

### 5.1. Identidade e estados

Cada unidade tem ID único, produto, receita, índice da próxima etapa,
localização e histórico com tempo simulado. Estados observáveis incluem:
no almoxarifado, em transporte, processando, aguardando retirada, no estoque
auxiliar, em validação, concluída e rejeitada.

Uma unidade ocupa exatamente uma localização. Uma máquina processa no máximo
uma unidade e permanece ocupada após terminar até a retirada. Uma vaga não
pode conter duas unidades. Revisitas a máquinas são permitidas pela receita.
Etapas consecutivas na mesma máquina podem prosseguir sem transporte extra.

### 5.2. Transporte e estoque auxiliar

1. Antes de coletar, reservar uma posição livre no destino.
2. Mover o conjunto vazio até a origem, coletar, elevar, deslocar, baixar e
   descarregar; cada fase tem duração positiva configurada no cenário.
3. Liberar a origem após concluir a coleta e ocupar o destino ao concluir a
   descarga. Reservas impedem que outra ação utilize a posição durante a viagem.
4. Levar a peça diretamente à próxima máquina quando disponível; caso esteja
   ocupada, usar o estoque auxiliar se houver vaga.
5. Se ambos estiverem indisponíveis, manter a peça na máquina de origem em
   estado de espera, sem inventar uma posição ou liberar a máquina antecipadamente.
6. Retirar do almoxarifado somente quando a primeira máquina puder receber.
   O estoque auxiliar é destinado à espera entre etapas nesta versão.

O estoque auxiliar recebe peças cuja operação anterior terminou. Retirar uma
peça no meio de uma operação e retomá-la depois permanece fora do escopo.

O despacho inicial será uma regra determinística demonstrativa: priorizar
retirada da validação para saída/rejeitados, depois retirada de máquinas com
operação concluída, depois peças do estoque auxiliar e, por último, entrada
de novas peças. Dentro da categoria, usar maior tempo de espera e ID como
desempate. Somente ações com destino disponível são elegíveis. Essa regra não
deve ser apresentada como otimização nem como garantia de ausência de bloqueios.

Se houver unidades pendentes, nenhuma ação elegível e nenhum evento futuro
capaz de liberar recursos, encerrar o avanço com **Simulação bloqueada** e
explicar os recursos envolvidos. Não manter uma reprodução infinita sem progresso.

### 5.3. Tempo, processamento e validação

O relógio simulado é a referência para processamento, transporte e histórico.
Máquinas distintas podem processar simultaneamente enquanto o transportador
executa outra tarefa. A taxa de quadros não deve alterar a ordem dos eventos
nem os resultados. Eventos simultâneos usam uma ordem estável documentada.

Na validação final, conferir ID esperado, produto e sequência completa de
operações. Aprovar somente unidades com histórico compatível; encaminhar as
demais à área de rejeitados, com motivo. Trata-se de validação lógica simulada,
sem confirmar qualidade física ou funcionamento de leitores reais.

## 6. Interface e controles

- **Iniciar**, **Pausar/Continuar**, **Reiniciar** e **Próximo evento**.
- Velocidades de reprodução de 0,5×, 1×, 2× e 4×, sem alterar as durações lógicas.
- Próximo evento disponível com a simulação pausada: avança ao próximo instante
  de mudança lógica e aplica os eventos desse instante na ordem definida.
- Pausar congela relógio e animações, inclusive durante uma coleta ou viagem;
  continuar retoma do mesmo ponto. Reiniciar restaura integralmente o cenário.
- Ao sair da área ou ocultar a aba, pausar; ao retornar, exigir continuar para
  evitar saltos de tempo e perda de acompanhamento.
- Selecionar uma peça na cena ou na lista textual mostra ID, produto, localização,
  etapas concluídas, próxima etapa e histórico.
- Painel com tempo simulado, unidades aprovadas/rejeitadas, ocupação do estoque
  auxiliar e estados das máquinas. Eventos descrevem origem, destino e motivo.
- Estado final explícito quando todas as unidades chegarem à saída/rejeitados.

Controles devem funcionar por teclado, com foco visível e nomes acessíveis.
Em telas pequenas, reorganizar painéis sem cortar controles. A lista textual
de unidades oferece as mesmas informações essenciais da seleção 3D.
Respeitar preferência por movimento reduzido, oferecendo transições mínimas
e avanço por evento. Em falta de suporte gráfico, mostrar explicação e manter
o acompanhamento textual; não apresentar uma área vazia como sucesso.

## 7. Cenário demonstrativo reproduzível

Proposta inicial de seis unidades, com três produtos e IDs exclusivos:

| Produto | Quantidade | Receita demonstrativa |
|---|---|---|
| A | 2 | M1 por 6 s → M2 por 16 s → M3 por 5 s |
| B | 2 | M1 por 4 s → M3 por 8 s |
| C | 2 | M3 por 5 s → M2 por 30 s |

Tempos de deslocamento, coleta, descarga e validação devem ficar explícitos
na configuração, em segundos simulados. Os valores iniciais e a ordem de
entrada devem ser ajustados e fixados na implementação para demonstrar ao
menos uma ida ao estoque auxiliar, uma saída dele e processamento paralelo.
Não declarar essas ocorrências verificadas apenas com a tabela acima.

Disponibilizar também cenários de validação controlados para estoque cheio,
bloqueio e rejeição por histórico inconsistente. Esses casos podem ser fixtures
de teste, sem exigir um editor ou formulário de falhas na interface final.

## 8. Organização técnica e evolução

Reutilizar o módulo React/TypeScript existente. Separar configuração do cenário,
estado/eventos da simulação, apresentação 3D e controles React. O relógio e as
regras devem poder ser testados sem renderização gráfica. A cena interpreta o
estado e interpola os movimentos; não decide sozinha quando uma etapa termina.

A implementação adotou Three.js diretamente no React e interpolação suave
baseada nos eventos, conforme a [ADR-008](../adr/0008-maquete-virtual-threejs.md).
A engine é carregada sob demanda, sem incluir o código gráfico nas outras telas.
Esta proposta não muda a tecnologia do backend nem transfere o otimizador
para o navegador: as regras locais servem exclusivamente à demonstração.

Não criar persistência ou contratos HTTP sem necessidade desta entrega.
Recursos gráficos e ciclos de animação devem ser liberados ao desmontar a tela.
Evitar renderizar toda a árvore React a cada quadro.

### Integração futura, não obrigatória para o aceite inicial

A SPEC-0005 considera transporte instantâneo e buffers ilimitados. A maquete
virtual introduz tempos de transporte e capacidade finita; portanto, reproduzir
um plano futuro exigirá um adaptador e tratamento de atrasos e bloqueios.

Ao conectar ordens e planejamentos, preservar o snapshot e as identidades,
distinguir tempos planejados de simulados e manter a qualidade retornada pelo
planejador. Uma prova de ótimo para o modelo atual não prova ótimo para o
modelo com transporte. Especificar essa integração separadamente, sem alterar
silenciosamente o contrato existente ou usar IDs demonstrativos como IDs reais.

## 9. Critérios de aceite

- [ ] CA-01: Área Simulação disponível no frontend, identificada como demonstração
  e utilizável sem backend ou hardware conectado.
- [ ] CA-02: Cena contém todos os elementos da seção 3, com posições alcançáveis,
  perspectiva, materiais, iluminação, sombras e identidade visual própria.
- [ ] CA-03: Ciclo de coleta, elevação, deslocamento e descarga é visível e suave,
  sem teletransporte, peças duplicadas ou atravessamento das estações.
- [ ] CA-04: Cenário padrão demonstra almoxarifado → máquinas → validação → saída,
  com processamento paralelo e uso efetivo do estoque auxiliar.
- [ ] CA-05: Capacidade, reservas, precedência, revisitas e espera por retirada
  são respeitadas; cenários de estoque cheio e bloqueio têm resultado explícito.
- [ ] CA-06: Pausa durante transporte, retomada, reinício, velocidades e próximo
  evento preservam estado e produzem os mesmos resultados lógicos.
- [ ] CA-07: Seleção e lista mostram identidade, localização e histórico corretos;
  validação distingue aprovação de rejeição com motivo.
- [ ] CA-08: Teclado, movimento reduzido, tela pequena, ausência de suporte gráfico
  e retorno à aba têm os comportamentos da seção 6.
- [ ] CA-09: Em desktop de referência documentado, cenário padrão em 1280×720
  mantém ao menos 30 FPS em 95% dos quadros medidos durante 60 s de reprodução
  ativa após aquecimento. Registrar navegador, hardware e qualidade gráfica;
  a meta não constitui garantia universal de desempenho.
- [ ] CA-10: Testes pertinentes, build e verificações do frontend passam; capturas
  e gravação de um ciclo completo são inspecionadas para validar o acabamento.
- [ ] CA-11: README do frontend documenta execução, controles, cenário, comandos
  de validação e limites; ADR registra as escolhas efetivas de renderização.

## 10. Plano de validação e entrega

1. Implementar e revisar uma cena estática com enquadramento, materiais, displays
   e iluminação antes de conectar a sequência completa de movimentos.
2. Testar o motor determinístico com relógio controlado: conservação das unidades,
   exclusividade de locais, reservas, precedência, simultaneidade, estoque cheio,
   ausência de progresso, reinício e validação de identidade/histórico.
3. Testar controles e integração com a cena, inclusive pausa no meio da viagem,
   troca de velocidade e sequência idêntica sob diferentes taxas de quadros.
4. Validar no navegador o cenário completo, seleção, câmera, teclado e viewport
   de 390 px. Capturar visão geral e estados de coleta, processamento e espera;
   gravar um ciclo para inspecionar continuidade e colisões visuais.
5. Medir desempenho conforme CA-09. Em ambientes de CI sem aceleração gráfica,
   separar testes de comportamento da medição visual em máquina de referência.
6. Executar em `frontend/` os comandos existentes `npm run check`,
   `npm run format:check`, `npm test`, `npm run build` e `npm run test:e2e`;
   ampliar os testes para a nova área e documentar novos comandos se necessários.
7. Registrar resultados, limitações e evidências no PR. Obter revisão de outro
   integrante antes do merge, conforme CONTRIBUTING.md.

A implementação e as evidências locais estão registradas na seção 12.
Validação mecânica e em hardware real permanece uma atividade separada.

## 11. Referências

- [SPEC-0006 — Frontend React](0006-react-frontend.md).
- [SPEC-0005 — Planejamento](0005-production-planning.md).
- [ADR-007 — Frontend local](../adr/0007-react-frontend.md).
- [Arquitetura](../architecture.md) e [visão geral](../visao-geral.md).
- [README do frontend](../../frontend/README.md).
- [README do planejador e hipóteses atuais](../../optimizer/README.md).
- [Regras de contribuição](../../CONTRIBUTING.md).


## 12. Implementação e evidências locais

Implementação autorizada pelo responsável após a criação desta spec. Incluídos
motor determinístico, área Simulação, geometria 3D própria, controles e seleção,
estoque auxiliar, processamento paralelo, validação e alternativa sem WebGL.
As escolhas estão na ADR-008. Nenhuma API, tabela ou migration foi alterada.

O cenário usa os tempos da seção 7, com M2 do produto C ajustada de 10 para 30 s
para evidenciar processamento paralelo. O ciclo termina com seis unidades
aprovadas, utiliza as duas vagas auxiliares e retira peças delas. O cenário não
é otimizado e pode bloquear se receitas/capacidades forem modificadas.

Validação executada em Windows, Node 24.15.0:

- Testes unitários: 27 aprovados, incluindo seis testes do motor com relógio
  controlado. Cobrem conservação/localização, reserva, estoque, paralelismo,
  ordem de eventos, revisitas, bloqueio e rejeição por inconsistência.
- Playwright: quatro testes aprovados no Chromium 156, incluindo os dois fluxos
  anteriores com API real e dois testes da simulação. API bloqueada somente para
  o cenário local; fallback WebGL, teclado, seleção, pausa, reinício e viewport
  de 390 px verificados. O erro de contexto WebGL no teste de fallback é esperado.
- Medição local: 60 s após 2 s de aquecimento, viewport 1280×720, Edge 155
  headless, Intel Core i5-13420H / Intel UHD Graphics via ANGLE Direct3D11,
  pixel ratio limitado a 1,5 e sombras de 2048 px. Foram observados 8.240
  intervalos requestAnimationFrame, percentil 95 de 8 ms durante reprodução
  ativa. É uma medição local de cadência, não garantia de FPS em outras GPUs.
- Uma gravação concorrente com outros testes apresentou maior custo; não usar
  esse resultado para prometer desempenho universal. A cena evita redesenho
  quando relógio e câmera permanecem parados.

Limitações: captura vertical conceitual, cenário em memória, sem integração
com planejamento ou hardware. A engine gráfica gera aviso de chunk acima de
500 kB no build; sua carga está isolada por importação dinâmica. CI remota e
revisão de outro integrante permanecem pendentes.
