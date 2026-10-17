# Estudo — Algoritmo para programação da produção

> **Status:** Proposta para discussão; não é decisão arquitetural aceita.
>
> **Data:** 13/10/2026
>
> **Escopo:** Revisão da SPEC-0004 e recomendação fundamentada nas atividades
> de Inteligência Computacional. Não implementa planejamento na API.

> **Restauração:** Conteúdo recomposto em 17/10/2026 a partir do histórico
> da conversa. A pesquisa e os experimentos não foram executados novamente.

## 1. Recomendação

Utilizar **Algoritmo Genético (AG) com elitismo**, adaptado ao problema de
**job shop**, para buscar uma programação que minimize o **makespan**:
o tempo entre o início da ordem e a conclusão da última unidade.

A escolha aproxima o Axion de dois trabalhos da Aula 04: a minimização de
makespan na distribuição de tarefas entre servidores e a busca por permutações
com seleção por torneio, crossover OX e mutação por troca. O componente novo
é o decodificador que transforma prioridades em um cronograma válido.

O AG encontra a melhor solução durante uma busca limitada; **não garante o
menor tempo possível em qualquer entrada**. Se o requisito exigir prova do
ótimo global, será necessário um método exato e tratar explicitamente os casos
em que o tempo disponível não permitir essa prova.

## 2. Relação com as atividades realizadas

Fontes examinadas no repositório `unifecaf-computational-intelligence`, commit
`2b843d3ffed6393f6a06b448ba7285423056a5d0`:

| Atividade | Evidência | Aplicação no Axion |
|---|---|---|
| [Aula 04 — roteiro, exercício 3][aula04-roteiro] | 20 tarefas, 4 servidores e objetivo explícito de minimizar makespan | Base para explicar objetivo e avaliação das soluções |
| [Aula 04 — alocação de servidores][aula04-servidores] | AG com população, torneio, crossover, mutação e elitismo | Estrutura principal da busca evolutiva |
| [Aula 04 — demonstração do professor][aula04-demo] | Permutações, crossover OX, mutação swap e torneio | Operadores adequados à representação de prioridades proposta |
| [Aula 08 — AG binário][aula08-ag] | Semente local, preservação do melhor e comparação com dez sementes | Modelo de experimento reproduzível; não reutilizar a codificação binária |
| [Aula 07 — resultados do lab 05][aula07-memetico] | Discussão de AG combinado com busca local | Possível evolução para algoritmo memético, depois de medir o AG inicial |

O exercício dos servidores permite escolher em qual servidor executar cada
tarefa independente. No Axion, a receita já fixa a máquina e a ordem das etapas.
Portanto, copiar `max(cargas_dos_servidores)` como fitness perderia as esperas
por etapas anteriores e poderia atribuir a mesma nota a cronogramas diferentes.

Também não basta usar a soma de todos os tempos: para uma demanda fixa essa
soma é constante, mesmo quando a programação aproveita melhor o paralelismo.

As aulas implementam os algoritmos explicitamente em Python, com NumPy em
várias atividades. Não há necessidade demonstrada de introduzir DEAP ou PyGAD
no MVP. NumPy pode ser usado se trouxer benefício mensurável; o experimento
deste estudo pode ser executado somente com a biblioteca padrão.

## 3. Como representar o problema do Axion

O [model de etapas](../backend/app/models/product_step.py) já fornece máquina,
sequência e duração. A [SPEC-0003](specs/0003-backend-products.md) permite
receitas diferentes e revisitar a mesma máquina. A modelagem geral recomendada
é job shop com máquinas fixas por operação e possíveis revisitas. A referência
oficial de [job shop do OR-Tools][jobshop] descreve precedência, exclusividade
de máquina e minimização do término do cronograma.

Para uma entrada como `Eixo: 2, Placa: 1`, criar no planejamento as unidades
lógicas `E1`, `E2` e `P1`, cada uma com sua própria cópia da receita. Não
transformar as duas unidades em uma operação com duração dobrada: isso imporia
um lote indivisível e impediria intercalações potencialmente melhores.

Esses identificadores são internos ao plano. A associação a uma peça física
identificada ocorre posteriormente; não implica cadastrar peças ao criar a ordem.

Hipóteses propostas para a primeira simulação:

- Uma ordem isolada, com todas as unidades e máquinas disponíveis no tempo zero.
- Uma operação por máquina por vez; máquinas diferentes podem trabalhar juntas.
- Cada unidade segue sua receita, sem sobrepor suas próprias etapas.
- Uma operação iniciada termina sem interrupção; tempos são determinísticos.
- Espera entre etapas permitida, com espaço de armazenamento suficiente.
- Transporte instantâneo, sem disputa pela mesa, setup, falhas ou bloqueio da
  estação depois de terminar o processamento.

O usuário confirmou em 13/10/2026 que as máquinas poderão processar peças
simultaneamente enquanto a mesa transporta outras. As demais condições acima
são hipóteses do estudo, não capacidades já validadas da maquete. O
[cadastro de máquinas](../backend/app/models/machine.py) contém apenas ID e nome;
não há calendário ou disponibilidade operacional implementados. No experimento,
"disponibilidade" é o horário calculado de liberação da máquina no próprio plano.

Com o início do horizonte em zero:

```text
fitness = makespan = maior horário de término entre todas as operações
```

## 4. Adaptação do AG das aulas

### Cromossomo

Usar uma permutação de **identificadores únicos de operações**, interpretada
como prioridade de programação. Exemplo ilustrativo:

```text
[E1.etapa2, P1.etapa1, E2.etapa1, E1.etapa1, P1.etapa2, E2.etapa2]
```

Essa lista não manda executar `E1.etapa2` antes de `E1.etapa1`. Ela fornece
prioridades ao decodificador, que só considera a próxima etapa ainda não
programada de cada unidade. Assim, preservamos o OX da aula sem violar receitas.
Não aplicar esse OX diretamente a `[E, E, P]`: seu tratamento de elementos
repetidos não preserva as quantidades exigidas por essa outra representação.

### Decodificador e avaliação

1. Criar um mapa da posição de cada operação no cromossomo.
2. Entre as próximas etapas das unidades, escolher a de menor posição no mapa.
3. Programar essa operação depois de sua predecessora e do último uso reservado
   da máquina:

   ```text
   início = max(término_da_etapa_anterior, liberação_da_máquina)
   fim = início + duração
   ```

4. Atualizar a próxima etapa da unidade e a liberação da máquina; repetir até
   programar todas as operações.
5. Retornar o cronograma e seu maior término como fitness.

"Predecessora programada" não significa que o tempo real já avançou até sua
conclusão: o algoritmo monta reservas futuras. Operações de máquinas diferentes
podem receber intervalos simultâneos. Essa versão acrescenta operações ao fim
da agenda de cada máquina; não procura encaixes em lacunas anteriores. É um
decodificador inicial simples, cuja qualidade deve ser avaliada nos experimentos.

As restrições obrigatórias ficam garantidas pela construção e verificadas por
um validador separado. Não usar uma multa de fitness como única proteção contra
sobreposição de máquinas ou inversão de etapas.

### Busca evolutiva

- Iniciar a população com uma solução de referência determinística e
  permutações aleatórias.
- Avaliar cada indivíduo pelo decodificador.
- Selecionar pais por torneio, favorecendo menor makespan.
- Aplicar crossover OX e mutação swap aos identificadores únicos.
- Copiar o melhor indivíduo para a geração seguinte (elitismo).
- Encerrar por orçamento de gerações/avaliações e devolver o melhor encontrado.

Incluir a referência na população e preservar o melhor garante que a busca
não devolva resultado pior que essa referência no mesmo modelo. Isso não
garante uma melhoria estrita: a referência já pode ser ótima.

População 40, 80 gerações, torneio de 3, crossover 0,8, mutação 0,2 por filho
e um indivíduo de elite são parâmetros experimentais, inspirados nas aulas.
Não são parâmetros aprovados ou ajustados ao desempenho final do Axion.
Entradas com uma única operação precisam dispensar os operadores que exigem
duas posições distintas. Usar gerador aleatório local e registrar a semente.

## 5. Revisão da SPEC-0004

A [SPEC-0004](specs/0004-production-orders.md) está coerente como cadastro da
demanda. Seu objetivo e seu escopo excluem explicitamente otimização. Portanto,
implementá-la integralmente ainda não entregará o planejamento solicitado.

| Ponto revisado | Parecer |
|---|---|
| Entrada com `product_id` e `quantity` | Adequada; o planejador carrega as receitas existentes |
| Ordem dos itens não representa prioridade | Manter; apresentação por ID não deve ser confundida com sequência de produção |
| Quantidades positivas, produtos existentes e gravação atômica | Manter |
| Não criar unidades físicas ao cadastrar a ordem | Manter; unidades lógicas do plano são outro conceito |
| Receitas referenciadas sem cópia | Coerente enquanto não houver edição; antes de permitir mudanças, definir preservação do plano e do histórico |
| Cadastro sem status de execução | Coerente com o escopo atual; não informar que uma ordem cadastrada já começou |
| Seção de persistência dizia "Produto e itens" | Corrigido para "Ordem e itens" |

Recomendação de entrega: manter a 0004 para demanda e criar uma próxima spec
de planejamento, com número confirmado no momento da abertura. O estudo não
aprova a 0004 nem substitui uma futura ADR sobre o algoritmo.

O próximo contrato deve produzir **um cronograma de operações**, e não apenas
uma lista de nomes de produtos. Proposta de conteúdo da resposta:

| Conteúdo | Finalidade |
|---|---|
| Produto, índice da unidade, etapa e máquina | Identificar exatamente cada operação |
| Início e fim em segundos relativos ao começo da ordem | Representar precedências e paralelismo |
| Makespan estimado | Medir o objetivo da busca |
| Makespan de referência e melhoria percentual | Explicar o ganho obtido |
| Algoritmo, versão, parâmetros e semente | Reproduzir a busca |
| Tempo gasto no cálculo | Separar custo computacional de tempo estimado de produção |
| Hipóteses utilizadas e evidência de otimalidade, quando existir | Evitar apresentar estimativa como medição física ou ótimo comprovado |

Também definir limites de unidades/operações e de trabalho da busca antes de
expandir quantidades. A quantidade positiva aceita no cadastro não precisa
significar capacidade ilimitada de planejamento síncrono.

A integração deverá seguir as ADRs aceitas: controller trata HTTP; service
carrega demanda e receitas por repositories e chama funções de otimização em
Python independentes de HTTP e do ORM. Avaliar cronogramas não requer consultas
ao banco em cada geração. Persistir planos, se aprovado, exige novas migrations
Alembic; não alterar revisões integradas ou inicialização da API.

O diretório do componente ainda não existe: `optimization/` aparece no guia de
contribuição, enquanto `optimizer/` aparece na arquitetura e na ADR-003. São
estruturas ilustrativas divergentes. Para uma implementação futura, a ADR-003
aceita é a referência, sem tratar o desenho proposto como diretório já existente.

## 6. Alternativas e critério de escolha

| Alternativa | Avaliação para esta entrega |
|---|---|
| AG com elitismo | Recomendado: conexão direta com makespan e operadores já praticados |
| PSO | As implementações das Aulas 05/08 trabalham variáveis contínuas; sequências exigiriam adaptação adicional |
| Colônia de formigas (ACO) | Viável; as aulas usam rotas/árvores, e seria necessário reconstruir escolha de operações elegíveis e custo do cronograma |
| Lógica fuzzy | As atividades da Aula 09 tratam inferência/controle; não fornecem por si só uma busca de cronogramas mínimos |
| Busca local / AG memético | Evolução possível após medir o AG inicial; a Aula 07 discute essa combinação |
| Enumeração ou CP-SAT | Referência para instâncias pequenas ou opção quando provar otimalidade for requisito |

O [CP-SAT distingue `OPTIMAL` de `FEASIBLE`][cpsat]. Um limite de execução pode
encerrar a busca sem provar o ótimo; usar um solver exato não elimina essa
distinção. Não há proposta de substituir a atividade de AG por essa ferramenta
na primeira entrega, nem necessidade de instalá-la para o experimento pequeno.

## 7. Experimento com as receitas existentes

O experimento original utilizou as receitas versionadas na
[migration do catálogo](../backend/migrations/versions/bb94b7e72eb7_insert_base_machines_and_products.py):

| Produto | Receita e duração em segundos |
|---|---|
| Eixo (E) | Torno 10 → Centro 15 |
| Placa (P) | Fresadora 15 → Centro 20 |
| Suporte (S) | Torno 10 → Fresadora 15 → Centro 20 |

Resultados executados em simulação em 13/10/2026, com as hipóteses da seção 3,
recuperados do histórico sem nova execução:

| Demanda | Prioridade E → P → S | Prioridade S → P → E | Menor duração da próxima etapa (SPT) | AG: melhor / média / pior |
|---|---:|---:|---:|---:|
| 1 E + 1 P + 1 S; 7 operações | 65 s | 80 s | 65 s | 65 / 65 / 65 s |
| 3 E + 2 P + 4 S; 22 operações | 175 s | 190 s | 175 s | 175 / 175 / 175 s |

As referências agrupam prioridades por produto, unidade e etapa; o mesmo
decodificador permite paralelismo em todas as alternativas. A regra SPT escolhe
a próxima etapa de menor duração entre aquelas cujas predecessoras já foram
programadas, desempatando pelo identificador interno. É uma política de
construção do plano, sem simular decisões online da máquina.

O AG foi executado com os parâmetros da seção 4, sementes de 0 a 9 e **população
inicial inteiramente aleatória**. A inclusão da referência na população é uma
recomendação para a integração futura, não uma característica desta medição.
O ótimo já estava na população inicial em 10/10 execuções pequenas e 6/10
execuções do caso maior. Portanto, os resultados não devem ser atribuídos
integralmente à evolução entre gerações.

Cada cronograma decodificado foi verificado quanto à presença única de todas
as operações, duração, precedência e ausência de sobreposição na mesma máquina.
No caso pequeno, foram enumeradas as 5.040 permutações de prioridade: mínimo
65 s, máximo 105 s e 717 cromossomos com o mínimo. Cromossomos diferentes podem
gerar o mesmo cronograma.

Além dessa enumeração, há uma prova simples para **estes dois casos e este
modelo**: o Centro precisa de 55 s ou 165 s de processamento e nenhuma peça
pode chegar a ele antes de 10 s. Logo, os limites inferiores são 65 s e 175 s.
Como existem cronogramas que atingem esses limites, esses valores são ótimos.
A prova não depende de supor que o decodificador enumere todos os cronogramas
possíveis do problema geral.

Exemplo do cronograma de 65 s:

| Máquina | Programação |
|---|---|
| Torno | E1: 0–10; S1: 10–20 |
| Fresadora | P1: 0–15; S1: 20–35 |
| Centro | E1: 10–25; P1: 25–45; S1: 45–65 |

O AG melhorou a referência S → P → E em 18,75% no caso pequeno e cerca de 7,89%
no maior, mas **empatou com E → P → S e SPT**. Isso valida a adaptação básica e
a importância de comparar referências; não demonstra superioridade do AG.
O catálogo atual tem um gargalo simples comum no Centro. Será necessário testar
receitas personalizadas mais variadas antes de afirmar vantagem de desempenho.

O [script restaurado](examples/estudo_ag_jobshop.py) utiliza somente a biblioteca
padrão e imprime JSON com resultados, cronogramas, configuração, sementes e
tempos de cálculo. Execute a partir da raiz do repositório, com Python 3.12
ou superior:

```powershell
python docs/examples/estudo_ag_jobshop.py
```

**Situação na restauração:** o script também foi recuperado em 17/10/2026,
a partir do histórico e do protótipo original preservado em arquivo temporário.
Foram verificadas a sintaxe e a formatação, sem reexecutar os experimentos.

A validação original foi realizada em CPython 3.14.4: execução completa em
aproximadamente 3,407 s naquele ambiente, incluindo enumeração, AG e verificações
de viabilidade. Ruff (formatação e lint) passou para o script original. Esses
resultados são históricos; não representam verificações feitas na restauração.
Os tempos de cálculo variam por computador; os tempos de produção da tabela
são estimativas do modelo. O experimento não acessou o banco nem executou a
maquete. A suíte do backend não foi executada, pois não houve alteração no
código da API, em dependências ou no banco. Não houve validação em hardware.

## 8. Pendências para a maquete e validação futura

O paralelismo entre estações foi confirmado pelo usuário. Ainda é necessário
definir quantas peças cabem em espera, quando uma máquina é liberada e os tempos
de deslocamento, carga e descarga. A mesa compartilhada pode exigir operações de transporte e
reservas próprias, além de bloqueios por falta de espaço. O cronograma simplificado
não deve ser enviado diretamente ao hardware sem validar essas restrições.

Critérios propostos para a futura implementação:

- Validar quantidades completas, identificação única das operações, duração,
  precedências, ausência de sobreposição por máquina e makespan reportado.
- Cobrir múltiplas unidades, receitas diferentes, revisitas à mesma máquina,
  uma operação e cenários em que não existe ganho de sequenciamento.
- Comparar políticas simples e AG usando as mesmas restrições e o mesmo
  simulador; executar várias sementes e registrar melhor/média/pior e tempo.
- Comparar pequenos casos com enumeração ou ótimo demonstrado; em casos maiores,
  informar diferença para uma referência ou limite inferior sem chamá-lo de ótimo.
- Acrescentar testes de transporte e validação em hardware antes da execução real.

## Referências das aulas

[aula04-roteiro]: https://github.com/thiago-fischer/unifecaf-computational-intelligence/blob/2b843d3ffed6393f6a06b448ba7285423056a5d0/AULA_04/roteiro_aula04_CIAO.md#L86-L96
[aula04-servidores]: https://github.com/thiago-fischer/unifecaf-computational-intelligence/blob/2b843d3ffed6393f6a06b448ba7285423056a5d0/AULA_04/exercicio_03_alocacao_servidores.ipynb
[aula04-demo]: https://github.com/thiago-fischer/unifecaf-computational-intelligence/blob/2b843d3ffed6393f6a06b448ba7285423056a5d0/AULA_04/demo_professor.py#L161-L274
[aula08-ag]: https://github.com/thiago-fischer/unifecaf-computational-intelligence/blob/2b843d3ffed6393f6a06b448ba7285423056a5d0/AULA_08/lab02_aula08.py#L55-L108
[aula07-memetico]: https://github.com/thiago-fischer/unifecaf-computational-intelligence/blob/2b843d3ffed6393f6a06b448ba7285423056a5d0/AULA_07/resultados_aula07.md#L73-L79
[jobshop]: https://developers.google.com/optimization/scheduling/job_shop
[cpsat]: https://developers.google.com/optimization/cp/cp_solver
