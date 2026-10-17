# SPEC-0005 — Otimização e cronograma da produção

> **Status:** Aprovada; implementada, aguardando revisão de outro integrante.
>
> **Data:** 17/10/2026
>
> **Aprovação:** 17/10/2026, por solicitação do responsável.
>
> **Diretriz do responsável:** AG obrigatório pela finalidade acadêmica;
> CP-SAT para verificar a solução e certificar o ótimo quando possível.

## 1. Objetivo e garantia de resultado

Gerar um cronograma que minimize o tempo total de uma ordem, explorando o
processamento simultâneo em máquinas diferentes e respeitando as receitas.
Atender produtos e máquinas cadastrados pelo usuário sem alterar o algoritmo,
inclusive quando esses cadastros ocorrerem imediatamente antes do planejamento.
Fornecer uma resposta que permita desenhar um Gantt por máquina e acompanhar
cada unidade entre suas etapas.

O objetivo é o **menor makespan global do modelo**, não a soma das durações,
o menor tempo de cálculo nem a maior ocupação de todas as máquinas. O AG é
obrigatório, mas não garante sozinho o ótimo. Um orçamento finito de busca
também não permite prometer prova do ótimo para toda entrada aceita.

Por isso, a API distingue:

- `optimal`: plano válido cujo makespan mínimo foi comprovado;
- `feasible`: plano válido, sem prova de ser mínimo.

O modo padrão exige prova: uma resposta com plano apenas viável **não satisfaz
o requisito de menor tempo comprovado**. O cliente pode solicitar explicitamente
o modo exploratório, que aceita o melhor plano disponível dentro do orçamento.
Ambos preservam a qualidade e as evidências na resposta. Nenhum plano desta
entrega está autorizado para execução física.

## 2. Referências e relação com o estudo

- [Estudo de otimização](../estudo-otimizacao-producao.md), especialmente
  modelagem, AG, contrato proposto, experimento e hipóteses da maquete.
- [SPEC-0001](0001-backend-machines.md),
  [SPEC-0003](0003-backend-products.md) e
  [SPEC-0004](0004-production-orders.md): cadastros e demanda existentes.
- [Arquitetura](../architecture.md), [visão geral](../visao-geral.md),
  [ADR-003](../adr/0003-monorepo.md),
  [ADR-004](../adr/0004-arquitetura-em-camadas-backend.md) e
  [ADR-005](../adr/0005-sqlalchemy-pydantic-alembic.md): referências aceitas.
- [ADR-006 proposta](../adr/0006-ag-cpsat-production-planning.md): justificativa
  da combinação entre AG e certificação exata; ainda não é decisão aceita.
- Fontes primárias: [job shop no OR-Tools][jobshop],
  [estados do CP-SAT][cpsat] e [limites da busca][limits], consultadas em
  17/10/2026. O uso concreto da biblioteca exige versão fixada e validação
  na implementação.

O estudo recomenda AG e identifica que uma exigência de ótimo comprovado
precisa de método exato. Esta spec acrescenta essa verificação mantendo o AG
obrigatório, conforme orientação do responsável. O catálogo fixo e o
decodificador que só acrescenta operações ao fim da máquina são características
do experimento; não devem limitar o planejador de produção.

"Sem receita fixa" significa **sem receita codificada no algoritmo**. Cada
produto ainda precisa de uma receita definida pelo usuário: sequência, máquina
e duração de cada etapa. O planejador não inventa etapas, não muda sua ordem
e não escolhe máquinas alternativas para uma etapa nesta entrega.

## 3. Escopo

### Incluído

- Planejar uma ordem já cadastrada, isoladamente, a partir das receitas atuais.
- Expandir quantidades em unidades lógicas independentes, sem formar um lote
  indivisível; permitir intercalações entre unidades do mesmo produto.
- Receitas heterogêneas, uma ou muitas etapas e revisitas à mesma máquina.
- AG com elitismo, referências determinísticas, validação independente,
  certificação CP-SAT e comparação transparente entre os resultados.
- Contrato HTTP síncrono com limites explícitos e saída independente de frontend.
- Snapshot da entrada, métricas, proveniência, limites de qualidade e cronograma.
- Testes do núcleo, integração HTTP e experimentos reproduzíveis.

### Fora desta entrega

- Interface Gantt, escolha de frontend, Grafana e publicação em cloud.
- Criar/editar máquinas ou produtos dentro da requisição de planejamento;
  reutilizar as rotas existentes de cadastro.
- Alterar a receita durante uma busca, edição/versionamento do catálogo,
  persistência de planos, listagem de planos ou execução de um plano salvo.
- Reserva de recursos entre ordens, replanejamento de uma produção em andamento,
  calendários, manutenção, liberação tardia de materiais e prioridades de entrega.
- Etapas paralelas da mesma unidade, rotas alternativas, capacidade maior que
  uma unidade por máquina ou processamento em lotes.
- Transporte, carga/descarga, setup, buffers limitados, bloqueios, falhas,
  associação a peças físicas e comunicação com o firmware.

Não implementar filas, workers distribuídos, SSE ou WebSocket nesta spec.
Caso os limites síncronos não atendam à demonstração, propor entrega separada
de cálculo assíncrono, sem ampliar silenciosamente o contrato.

## 4. Modelo do problema

### 4.1. Entrada e identidade

Carregar ordem, quantidades, produtos, etapas e máquinas por repositories.
Capturar esses dados em um snapshot imutável e liberar a sessão antes da busca.
Não executar consultas durante gerações ou dentro do solver.

| Elemento | Regra |
|---|---|
| Produto | ID opaco e nome; nenhuma regra pode depender do nome ou de IDs do catálogo inicial |
| Máquina | ID opaco; construir mapeamento interno para solver, sem presumir IDs consecutivos |
| Receita | Etapas `sequence` de 1 a N, com `machine_id` e `processing_time_seconds` |
| Unidade lógica | Uma por quantidade; índice de 1 a Q por produto |
| Operação | Uma etapa de uma unidade; identidade única mesmo em revisitas à máquina |
| Tempo | Segundos inteiros; duração positiva; início e fim inteiros não negativos |

Ordenar produtos por ID, unidades por índice e etapas por sequência para
construir a entrada canônica. IDs de unidade: `p{product_id}-u{unit_index}`;
IDs de operação: `{unit_id}-s{sequence}`. São únicos no snapshot daquela ordem,
não globalmente; não equivalem à identificação de matéria-prima.

O snapshot contém somente produtos demandados e máquinas usadas por suas
receitas, com nomes copiados para apresentação. Cada nova chamada captura
novo snapshot; cadastros novos não exigem reiniciar a aplicação nem retreinar
o AG. Produtos diferentes podem ter nomes e receitas iguais.

### 4.2. Restrições obrigatórias

Para cada operação `o`, com duração `d[o]`, definir início `s[o]` e fim `e[o]`:

```text
s[o] >= 0
e[o] = s[o] + d[o]
s[próxima etapa da unidade] >= e[etapa anterior]
operações da mesma máquina não se sobrepõem
Cmax = max(e[o])
minimizar Cmax
```

Intervalos são semiabertos `[início, fim)`: uma máquina pode iniciar a próxima
operação exatamente quando termina a anterior. Cada operação aparece uma vez
e usa exatamente a máquina da receita. Uma unidade nunca executa duas etapas
ao mesmo tempo. Máquinas distintas podem operar simultaneamente, inclusive
processando unidades diferentes do mesmo produto. Não serializar produtos
inteiros nem impor um fluxo único de máquinas a todas as receitas.

Todas as unidades e máquinas estão disponíveis em `t=0`. Operações são
determinísticas e não interrompidas. Esperas são permitidas com buffer
ilimitado. Transporte é instantâneo e não consome recursos. São hipóteses do
modelo `job_shop_v1`, não propriedades comprovadas da maquete.

Uma espera pode ser necessária em um ótimo. Não acrescentar obrigação de manter
todas as máquinas ocupadas nem otimizar utilização antes do makespan.

### 4.3. Horizonte e limites de qualidade

Um plano completamente sequencial é sempre viável para uma entrada válida deste
modelo. Seu tempo `H = soma(d[o])` é horizonte superior suficiente.
Calcular com inteiros Python e validar os limites antes de criar variáveis.

Limite inferior analítico inicial:

```text
L_route = maior soma das durações de uma unidade
L_machine = maior soma das durações atribuídas a uma máquina
L = max(L_route, L_machine)
L <= ótimo <= melhor makespan válido conhecido
```

Esses limites são válidos para receitas arbitrárias, mas podem ser fracos.
Usar também limites certificados pelo solver, sempre sobre o mesmo modelo.
Não transformar o argumento específico do Centro do estudo em regra geral.

## 5. Pipeline de otimização

### 5.1. Referências obrigatórias

Construir duas referências pelo mesmo decodificador usado pelo AG:

1. Prioridade canônica por produto, unidade e etapa.
2. Menor duração da próxima etapa elegível (SPT); desempate por produto,
   índice da unidade e sequência.

Uma etapa é elegível quando sua predecessora foi **programada**, não quando
um relógio da simulação já avançou até seu término. A regra apenas constrói
reservas. Registrar os makespans de ambas; a referência oficial é a de menor
makespan, com desempate pela prioridade canônica.

### 5.2. AG obrigatório

- Cromossomo: permutação de IDs únicos de operações. A posição significa
  prioridade, não execução literal antes de uma predecessora.
- Decodificador: selecionar, entre as próximas etapas elegíveis das unidades,
  aquela de menor posição no cromossomo.
- Reservar a operação no **primeiro intervalo livre suficiente** da máquina
  após o fim da predecessora; procurar também lacunas entre reservas, não
  apenas o fim da agenda. Não mover operações já reservadas.
- Fitness: makespan do cronograma válido. Empates podem manter o primeiro
  indivíduo; não é necessário achar uma programação única.
- Incluir as duas referências na população inicial e completar com permutações
  aleatórias; permitir repetidos se o espaço for menor que a população.
- Seleção por torneio, crossover OX, mutação swap e elitismo. OX trabalha
  IDs únicos, nunca nomes repetidos de produto.
- Preservar o melhor resultado durante toda a busca. O AG não pode entregar
  plano pior que a referência oficial.
- Tratar uma operação sem crossover/swap. Usar gerador aleatório local;
  não alterar o estado aleatório global da aplicação.
- Reavaliar todo filho modificado; cache pode usar cromossomo e snapshot,
  nunca misturar avaliações de ordens diferentes.

Perfil inicial proposto, inspirado no estudo: população 40, até 80 gerações,
torneio de 3, crossover 0,8 por par, swap com probabilidade 0,2 por filho e
um indivíduo de elite. Registrar perfil e valores efetivos. Encerrar no
primeiro limite de gerações ou tempo atingido, preservando o melhor avaliado.
Esses valores exigem medição; não constituem desempenho já demonstrado.

Guardar `initial_best_makespan_seconds`, `best_makespan_seconds`, gerações
concluídas, avaliações sem cache e motivo de término. Não atribuir ao processo
evolutivo um ótimo que já estivesse na população inicial.

### 5.3. Verificação e certificação CP-SAT

Após o AG, criar modelo completo com variáveis de intervalo para cada operação,
precedências, `NoOverlap` por máquina e minimização de `Cmax`.
Usar o plano do AG como sugestão e seu makespan como limite superior.
O solver pode buscar qualquer cronograma do modelo, sem se limitar aos
cromossomos visitados ou ao conjunto gerado pelo decodificador.

CP-SAT é o mecanismo de verificação e certificação; se encontrar plano melhor,
o resultado final deve aproveitar a melhoria. **Não esconder sua autoria:**
conservar métricas do AG e do CP-SAT separadamente e informar
`selected_source = genetic_algorithm | cp_sat`. Em empate, manter o cronograma
do AG e usar a evidência do solver para certificá-lo, quando aplicável.
O AG continua obrigatório em toda chamada aceita; não pode virar um campo
decorativo sem executar a construção e avaliação de sua população.

| Resultado do solver | Tratamento |
|---|---|
| `OPTIMAL` | Validar candidato e provar o makespan; tolerâncias de gap absoluto e relativo devem ser zero |
| `FEASIBLE` | Comparar candidato válido com AG e preservar o menor; não inferir ótimo apenas pelo status |
| `UNKNOWN` | Preservar plano válido do AG; ausência de solução do solver não é inviabilidade |
| `INFEASIBLE` | Erro interno: há plano válido conhecido dentro do horizonte; não apresentar como impossibilidade de produção |
| `MODEL_INVALID` | Erro interno de modelagem; não retornar um plano como resultado normal |

Calcular `lower_bound_seconds` como o maior limite inferior válido conhecido
e `upper_bound_seconds` como o makespan escolhido. Manter `0 < L <= U`.
Limites fracionários do solver devem ser convertidos conservadoramente para
inteiros sem arredondar para cima a partir de um valor de apresentação.
Usar `floor` conservador; não declarar prova porque uma porcentagem arredondou
para zero. Uma evidência válida `L == U` também comprova o ótimo, mesmo quando
o status bruto não é `OPTIMAL`.

```text
absolute_gap_seconds = U - L
relative_gap_percent = 100 * (U - L) / U
improvement_percent = 100 * (baseline_makespan - U) / baseline_makespan
```

`relative_gap_percent` é o intervalo de incerteza relativo ao melhor plano,
não a diferença conhecida para o ótimo. A melhoria usa a referência oficial,
com o mesmo snapshot e restrições. Pode ser zero. Exibir percentuais com duas
casas, mas decidir qualidade usando valores integrais e evidências.

Falha inesperada do solver ou plano que falhe no validador retorna erro interno,
sem mascarar a falha como término normal por orçamento.

### 5.4. Validador independente

Verificar antes de responder: operações esperadas exatamente uma vez; identidades,
máquinas e durações iguais ao snapshot; tempos inteiros; precedências; ausência
de sobreposição por máquina e unidade; makespan; métricas e limites coerentes.
O validador não pode reaproveitar o estado de disponibilidade do decodificador
como única evidência, nem depender de `assert` removível com `python -O`.
Para CP-SAT, validar o candidato antes de aceitá-lo; validar novamente o plano
final serializado. Erros devem identificar a regra no log, sem expor detalhes
internos no HTTP.

## 6. Limites operacionais propostos

| Limite | Valor inicial |
|---|---:|
| Unidades totais da ordem | 100 |
| Operações após expansão | 1.000 |
| Máquinas distintas usadas | 50 |
| Horizonte H | 1.000.000.000 s |
| Tempo do AG | padrão 3 s; inteiro de 1 a 20 |
| Tempo de certificação | padrão 7 s; inteiro de 1 a 20 |
| Soma dos dois orçamentos | até 30 s |
| Semente | padrão 0; inteiro de 0 a 2.147.483.647 |

Calcular contagens e H por multiplicação/soma das receitas **antes de expandir**
quantidades; rejeitar excesso sem criar milhares de objetos ou iniciar a busca.
Esses limites se aplicam ao planejamento, sem mudar o cadastro da SPEC-0004.

Orçamentos são de busca por fase, não promessa de latência HTTP total.
Registrar tempo de preparação, AG, certificação e total de planejamento com
relógio monotônico; o total inclui preparação e validação e exclui transmissão.
Verificar prazo entre avaliações do AG; documentar possível excedente de uma
avaliação e a tolerância observada do solver. Uma requisição não altera o
orçamento de outra. Inicialmente usar um worker de busca do CP-SAT por chamada.
Aplicar a semente da requisição também ao CP-SAT e registrar o valor efetivo.

Limitar a uma busca ativa por processo da API, com liberação do controle em
sucesso ou falha e sem manter transação de banco durante a busca. Nova chamada
concorrente recebe `503` e `Retry-After: 1`, sem fila ilimitada. Documentar que
esse controle é local ao processo e medir impacto nas demais rotas. Aumentar
workers/processos exige reavaliar o limite total de CPU/memória.

Os limites são propostas conservadoras para validação, não capacidade medida.
Antes da entrega, medir as entradas de fronteira e reduzir limites se preciso;
atualizar spec, README e testes. Não aumentar limites sem evidência.

## 7. Contrato HTTP proposto

### 7.1. Requisição

`POST /orders/{order_id}/plan`, sem prefixo de versão, acompanhando a API atual.
Corpo JSON obrigatório; `{}` usa os padrões abaixo:

```json
{
  "optimality_policy": "require_proof",
  "ga_time_limit_seconds": 3,
  "certification_time_limit_seconds": 7,
  "seed": 0
}
```

`optimality_policy`: `require_proof` (padrão) ou `allow_feasible`.
Tipos inteiros estritos, sem aceitar booleanos, strings ou decimais; rejeitar
nulos e campos extras. O cliente não informa receitas, máquina, makespan,
parâmetros de operadores ou resultado do solver por esta rota.

Validar estrutura e parâmetros; existência da ordem; integridade do snapshot
e limites; capacidade de cálculo. `order_id` deve ser inteiro positivo.
Não modificar ordem, receitas ou máquinas, nem reservar recursos. A chamada
calcula uma resposta transitória; não cria recurso persistido nem retorna `201`.

| Condição | HTTP e conteúdo |
|---|---|
| Plano `optimal`, qualquer política | `200`, envelope completo |
| Plano `feasible`, `allow_feasible` | `200`, envelope completo sem alegar mínimo |
| Plano `feasible`, `require_proof` | `409`, `code: optimality_not_proven` e `result` com o mesmo envelope completo, permitindo inspecionar o candidato |
| Ordem positiva inexistente | `404`, `detail: Ordem de produção não encontrada.` |
| Estrutura, parâmetros, ID ou limites inválidos | `422` |
| Busca já ativa no processo | `503`, `code: planning_busy`, `detail` genérico e `Retry-After: 1` |
| Dados persistidos inconsistentes, falha do solver ou validação interna | `500` genérico; diagnóstico somente no log |

O `409` significa ausência de prova dentro do orçamento, não invalidez do plano
nem inviabilidade da ordem. Não tentar executar automaticamente o candidato.
Não são necessários `GET /plans`, status de produção ou migration nesta entrega.

Erro de limite segue estrutura estável:

```json
{
  "detail": "A ordem excede os limites de planejamento.",
  "code": "planning_limits_exceeded",
  "violations": [
    {"field": "operation_count", "actual": 1200, "limit": 1000}
  ]
}
```

Listar todas as violações calculadas em ordem de `field`. Erros Pydantic usam
`detail` no formato existente, sem fixar texto interno da biblioteca.

### 7.2. Envelope da resposta

O [exemplo completo](../examples/planning-response.json) é ilustrativo e inclui
todas as sete operações do cronograma de 65 s do estudo. Não representa
execução nova do AG ou CP-SAT. Tempos de cálculo e versões são ilustrativos.

| Campo | Contrato |
|---|---|
| `schema_version` | `1`; versão do formato, não da rota |
| `order_id` | Ordem utilizada |
| `model_version` | `job_shop_v1` |
| `time_unit` | `seconds`; origem sempre zero |
| `quality` | `optimal` ou `feasible` |
| `optimality_proven` | Booleano coerente com qualidade e prova |
| `selected_source` | `genetic_algorithm` ou `cp_sat` |
| `execution_ready` | Sempre `false` nesta entrega |
| `assumptions` | Objeto com hipóteses explícitas do modelo, conforme exemplo |
| `input_snapshot` | Ordem expandível: itens com ID, nome, quantidade e receita, e máquinas com IDs/nomes; listas ordenadas por ID e etapas por sequência |
| `metrics` | Makespan, unidades/operações, limites inferior/superior, gaps, referência oficial e melhoria |
| `search` | Implementação/versão do planejador, semente, perfil efetivo do AG, resultados das referências, fases e tempos |
| `proof` | `method: cp_sat | analytical_bound | none`, versão do solver e status bruto; `lower_bound_seconds` coerente com métricas |
| `operations` | Lista completa de operações para Gantt |
| `machine_metrics` | Uma entrada por máquina usada: tempo ocupado, ocioso e utilização |

`search` registra `ga` com parâmetros efetivos, gerações, avaliações, melhor
inicial/final e motivo `generation_limit | time_limit | trivial_instance`;
`certification` com orçamento, tempo, status bruto e makespan do candidato do
solver (`null` se não houver). Registrar versão real do solver e do núcleo na
implementação; não copiar valores ilustrativos do exemplo para produção.

`proof.method = cp_sat` exige status `OPTIMAL` com tolerâncias zero ou limite
inferior válido do solver igual a U. `analytical_bound` exige L analítico igual
a U; `none` significa ausência de prova. Não usar versão ou semente como prova.
O status bruto do solver é informativo, distinto da qualidade do plano final.

### 7.3. Operações e métricas para Gantt

| Campo de cada operação | Regra |
|---|---|
| `operation_id` | Identidade lógica única no snapshot |
| `unit_id`, `unit_index` | Unidade lógica e índice dentro do produto |
| `product_id` | Produto da unidade; nome em `input_snapshot` |
| `step_sequence` | Etapa da receita, iniciando em 1 |
| `machine_id` | Máquina da etapa; nome em `input_snapshot` |
| `start_seconds`, `end_seconds` | Intervalo semiaberto desde zero |
| `duration_seconds` | Exatamente `end_seconds - start_seconds` e duração da receita |
| `predecessor_operation_id` | `null` na primeira etapa; ID da etapa imediatamente anterior nas demais |
| `waiting_seconds` | Início menos fim da predecessora; na primeira etapa, início menos zero |

Ordenar `operations` por `(start_seconds, machine_id, product_id, unit_index,
step_sequence)`, sem remover operações simultâneas. A ordem do array não é uma
ordem global de execução. IDs/números são dados, não cores ou coordenadas.
O cliente agrupa por `machine_id`, usa início/fim no eixo temporal e colore
por `product_id`, rotulando unidade/etapa. Selecionar `unit_id` permite acompanhar
a peça em máquinas diferentes; `predecessor_operation_id` permite mostrar suas
dependências. Não incluir HTML, biblioteca de gráfico, percentuais de posição,
datas de calendário fictícias ou códigos de cor na API.

Para cada máquina usada:

```text
busy_seconds = soma das durações de suas operações
idle_seconds = makespan_seconds - busy_seconds
utilization_percent = 100 * busy_seconds / makespan_seconds
```

O tempo ocioso considera todo o horizonte `[0, makespan)`, incluindo antes da
primeira e depois da última operação. Ociosidade não prova gargalo ou falha de
otimização. Não inventar blocos de operação para esperas; o Gantt deriva lacunas.
O cursor usa `[início, fim)` para determinar qual operação está ativa. Isso é
simulação do plano, não telemetria real nem status de máquina persistido.

## 8. Arquitetura e persistência

O núcleo deve receber estruturas Python tipadas, independentes de FastAPI,
SQLAlchemy e sessões. Uma função de planejamento coordena referências, AG,
certificação e validação; classes genéricas de plugins não são necessárias.

Proposta de organização, a confirmar na implementação conforme estrutura real:

```text
optimizer/
  pyproject.toml
  README.md
  src/axion_optimizer/
    domain.py
    decoder.py
    genetic_algorithm.py
    certification.py
    validation.py
    planner.py
  tests/
backend/app/
  controllers/planning_controller.py
  services/planning_service.py
  schemas/planning_schema.py
```

O diretório foi criado nesta implementação. `optimizer/` segue a referência da ADR-003 aceita;
`optimization/` aparece como desenho alternativo no README/CONTRIBUTING e não
deve motivar dois componentes. Formalizar empacotamento local em `optimizer/`,
com import `axion_optimizer`, dependência local explícita do backend e lockfile
atualizado; não alterar `sys.path` em runtime. Definir versões compatíveis de
Python/OR-Tools e registrar instalação limpa na CI antes de entregar código.

Controller trata HTTP. Service carrega snapshot por repositories, aplica
limites, libera a sessão e chama núcleo. Repositories existentes podem ser
estendidos para carregar demanda/receitas/máquinas em lote. Schemas de entrada
e saída continuam separados dos models. Não criar model ORM para cromossomos.

Esta spec não persiste planos e, portanto, não adiciona migration. Se a equipe
decidir persistir planos/histórico, isso exige extensão explícita da spec,
snapshot durável e nova revisão Alembic; não alterar revisões integradas nem
usar `create_all()`. Não adicionar implicitamente execução ou status à ordem.

## 9. Testes e critérios de aceite

Os critérios abaixo são acompanhados pelos testes e medições em
[Validação da SPEC-0005](../planning-validation.md). A revisão humana antes
do merge continua obrigatória; a ADR-006 permanece Proposta.

- [x] CA-01: Máquinas/produtos novos, IDs não consecutivos, nomes repetidos e
  quantidades variadas funcionam sem alterar código, reiniciar ou retreinar.
- [x] CA-02: Receitas de tamanhos diferentes, ordens distintas de máquinas,
  revisitas e etapas consecutivas na mesma máquina são respeitadas.
- [x] CA-03: Duas operações independentes de 10 s em máquinas distintas
  terminam em 10 s; na mesma máquina, terminam em 20 s.
- [x] CA-04: Duas unidades da receita M1/10 → M2/10 terminam em 30 s,
  demonstrando que as quantidades não viram lote indivisível de 40 s.
- [x] CA-05: O decodificador preenche lacunas: U1=M1/10 → M2/5,
  U2=M2/5, prioridade U1.s1,U1.s2,U2.s1 resulta em U2.s1 de 0–5,
  U1.s2 de 10–15 e makespan 15; o acréscimo somente ao fim daria 20.
- [x] CA-06: AG executa obrigatoriamente, preserva referências e elitismo;
  operadores mantêm permutação válida, quantidades e todas as operações.
- [x] CA-07: Uma operação e espaços pequenos não causam falha em OX/swap;
  o melhor inicial é registrado separadamente do melhor final.
- [x] CA-08: Certificador considera todo o modelo e usa AG como sugestão/limite,
  não como restrição indevida às programações que pode explorar.
- [x] CA-09: Caso controlado em que CP-SAT melhora o AG retorna a melhoria com
  origem `cp_sat`; empate mantém AG; métricas de ambos permanecem acessíveis.
- [x] CA-10: `OPTIMAL`, `FEASIBLE`, `UNKNOWN`, `INFEASIBLE` e `MODEL_INVALID`
  têm tratamentos testados com adaptador controlado, sem depender de timeout
  aleatório para cobrir cada ramo. Testar também integração real do solver.
- [x] CA-11: Limites, gap, prova e melhoria são coerentes; arredondamento
  percentual não produz falsa certificação; tolerâncias de gap são zero.
- [x] CA-12: Sem prova, política padrão retorna `409` com candidato válido;
  `allow_feasible` retorna `200` com qualidade `feasible`. Com prova, `200`.
- [x] CA-13: Validador rejeita operação faltante/duplicada, troca de máquina,
  duração alterada, inversão de etapa, sobreposição e métricas adulteradas.
- [x] CA-14: O cronograma de 65 s do estudo é válido e casos históricos podem
  atingir/provar 65 s e 175 s no mesmo modelo, sem exigir mesmas barras ou IDs.
- [x] CA-15: Casos pequenos personalizados com até oito operações são
  comparados com um oráculo independente que enumera ordens por máquina,
  elimina ciclos com precedências e calcula inícios mais cedo em cada DAG.
  Não usar somente permutações do decodificador como prova do ótimo geral.
- [x] CA-16: Testes gerados com sementes fixas verificam invariantes em receitas
  variadas, máquinas esparsas, revisitas e quantidades; makespan do AG é menor
  ou igual ao da referência oficial e limites inferiores não ultrapassam o
  ótimo do oráculo.
- [x] CA-17: Mesma entrada e semente, com limite fixo de gerações e sem corte
  por relógio no teste, reproduzem o AG. Não exigir barras idênticas sob timeout
  ou versões diferentes do solver; registrar versões, parâmetros e hardware.
- [x] CA-18: Contagens/H são limitados antes da expansão; testar fronteiras e
  excesso, parâmetros estritos e concorrência com liberação após falhas.
- [x] CA-19: Resposta pode ser agrupada por máquina e filtrada por unidade,
  com todas as dependências, esperas e durações e ordenação determinística.
  Validar também o exemplo JSON contra o schema implementado.
- [x] CA-20: API cobre `404`, `422`, `409`, `503` e `500`; não grava unidades
  físicas, planos ou estados de execução e não mantém sessão durante a busca.
- [x] CA-21: Instalação limpa, suíte do núcleo/backend, lint, formatação e CI
  passam; READMEs contêm instalação, execução, teste e limites efetivos.
- [x] CA-22: Experimentos usam várias sementes, referências e entradas variadas;
  publicam ganho, gap, frequência de prova, melhor/média/pior e custo de cálculo,
  distinguindo contribuição do AG de melhorias exclusivas do certificador.

## 10. Plano de implementação e validação

1. Seguir o escopo aprovado desta spec e revisar a ADR-006 proposta,
   preservando a obrigatoriedade do AG.
2. Criar núcleo tipado, gerador de unidades e limites de entrada; implementar
   referências, validador e decodificador com encaixe em lacunas.
3. Implementar AG e registrar sua contribuição com testes determinísticos.
4. Integrar CP-SAT, testes reais e tratamento controlado dos estados; provar
   os casos pequenos e comparar com o oráculo independente.
5. Integrar service/controller/schemas; validar resposta e exemplo de Gantt.
6. Medir qualidade/tempo/memória em catálogo inicial e receitas personalizadas,
   incluindo entradas de fronteira; ajustar limites documentados.
7. Atualizar instalação do backend, README do núcleo e CI para executar ambos;
   obter revisão de outro integrante antes de merge, conforme CONTRIBUTING.

Comandos já disponíveis no backend, a partir de `backend/`:

```powershell
uv sync --locked --python 3.12
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```

O [README do núcleo](../../optimizer/README.md) documenta instalação isolada,
uso Python, testes e experimentos. O script
histórico `python docs/examples/estudo_ag_jobshop.py` continua sendo somente
experimento de catálogo fixo, não implementação desta spec.

### Evidências desta entrega documental (17/10/2026)

- JSON de exemplo lido com `JSON.parse` e verificado por script Node.js:
  sete operações únicas, cobertura exata do snapshot, durações, precedências,
  esperas, ordenação, ausência de sobreposição por máquina e métricas coerentes.
- Enumeração independente das 24 combinações de ordens por máquina do exemplo,
  com precedências e cálculo de caminhos no DAG: mínimo de 65 s, igual ao plano.
  Essa verificação não executou o AG nem o CP-SAT.
- Verificados 33 links locais nos cinco documentos envolvidos, incluindo os
  links para os arquivos novos; `git diff --check` sem erros.

Essas evidências documentais precedem a implementação. A validação real está em
[Validação da SPEC-0005](../planning-validation.md), com suítes do núcleo/backend,
instalação de OR-Tools, oráculo independente e medições de qualidade/tempo/memória.
O JSON documental continua ilustrativo; os relatórios experimentais são separados.
Nenhuma dessas verificações comprova funcionamento em hardware.

## 11. Pendências e evolução física

Antes da execução real, definir capacidade dos buffers, liberação de máquinas,
tempos de deslocamento/carga/descarga e disputa pela mesa. O transporte poderá
precisar de operações e uma linha própria no Gantt. Isso muda o modelo, seus
limites inferiores e a interpretação de ótimo; exige nova versão explícita,
novos testes e validação em hardware.

Uma máquina cadastrada representa um recurso lógico da simulação; cadastrá-la
não cria equipamento físico. O snapshot desta spec preserva a interpretação
da resposta transitória, mas não substitui política de edição/histórico para
planos duráveis. Prova do ótimo de `job_shop_v1` não é prova do menor tempo da
maquete enquanto transporte e demais restrições físicas estiverem ausentes.

[jobshop]: https://developers.google.com/optimization/scheduling/job_shop
[cpsat]: https://developers.google.com/optimization/cp/cp_solver
[limits]: https://developers.google.com/optimization/cp/cp_tasks
