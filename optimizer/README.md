# Planejador de produção do Axion

Implementação da [SPEC-0005](../docs/specs/0005-production-planning.md).
O pacote `axion_optimizer` recebe um snapshot imutável de receitas e demanda,
expande unidades lógicas e devolve um cronograma transitório `job_shop_v1`.
Não depende de FastAPI, SQLAlchemy, banco ou catálogo inicial.

## Instalação e validação

Python 3.12–3.14; validação realizada em **3.12.13**, OR-Tools **9.15.6755**.
O backend instala este pacote por dependência local explícita; clone o monorepo
completo. Para trabalhar somente no núcleo, a partir de `optimizer/`:

```powershell
uv sync --locked --python 3.12
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python -m axion_optimizer.experiments --output ../docs/examples/planning-benchmark.json
```

O último comando executa 30 buscas reais e sobrescreve o relatório experimental.
Os lockfiles de backend e núcleo são independentes; ao modificar dependências
compartilhadas, atualize ambos com `uv lock` nos respectivos diretórios.

## Uso Python

```python
from axion_optimizer.domain import Item, Machine, Snapshot, Step
from axion_optimizer.planner import plan

snapshot = Snapshot(
    items=(Item(17, "Produto personalizado", 2, (Step(1, 42, 10), Step(2, 99, 10))),),
    machines=(Machine(42, "Estação A"), Machine(99, "Estação B")),
)
result = plan(snapshot, order_id=1, seed=0)
print(result["quality"], result["metrics"]["makespan_seconds"])  # optimal, 30
```

Produtos/máquinas devem estar ordenados por ID e etapas por sequência, com
somente as máquinas utilizadas. `prepare()` verifica integridade e limites
antes da expansão. Cada unidade possui sua própria precedência; revisitas e
etapas consecutivas na mesma máquina são permitidas.

O núcleo devolve o melhor plano validado e suas evidências. A política HTTP
`require_proof` pertence ao backend. O chamador Python deve verificar `quality`
e respeitar os limites de orçamento da spec. O controle de uma busca ativa
por processo fica no service da API; chamadas Python diretas não o aplicam.

## Busca e garantias

As referências canônica e SPT usam o mesmo decodificador do AG: prioridade entre
próximas etapas elegíveis e reserva no primeiro intervalo livre após a
predecessora. O cromossomo contém IDs únicos de operações. O AG usa população
40, até 80 gerações, torneio 3, crossover OX 0,8, mutação swap 0,2 e elite 1.
O RNG é local e o cache de fitness pertence a uma única busca; agendas completas
não ficam acumuladas no cache. Uma operação dispensa crossover/swap.

As duas referências são avaliadas obrigatoriamente. Se o prazo encerrar durante
a população inicial, as posições restantes recebem cópias do melhor avaliado.
Nas gerações, o prazo é conferido entre avaliações; filhos de uma geração
incompleta ainda podem melhorar o resultado. O melhor inicial é registrado
antes da evolução, separadamente do final. Nos testes, `run_ga(..., time_limit=None)`
permite reproduzir gerações fixas sem interferência do relógio.

O CP-SAT recebe intervalos, precedências e `NoOverlap`, com sugestão do AG,
seu makespan como limite superior e o modelo completo para buscar melhorias.
Usa um worker, a semente solicitada e gaps absoluto/relativo zero.
Melhorias são atribuídas ao CP-SAT; empate conserva as barras do AG.
Limites fracionários são convertidos com `floor`. `UNKNOWN` preserva o AG;
`INFEASIBLE`, `MODEL_INVALID`, falhas e candidatos inválidos geram erro interno.

`optimal` exige prova exata ou limite inferior igual ao makespan. `feasible`
preserva um plano válido com incerteza explícita. O validador independente
reconfere cobertura, identidades, durações, precedências, não sobreposição,
esperas, métricas e prova, inclusive após serialização no backend.

## Limites e evidências

Até **100 unidades, 1.000 operações, 50 máquinas e horizonte de 1 bilhão de
segundos**; contados por soma/multiplicação antes de expandir unidades.
Orçamentos HTTP: AG 3 s e CP-SAT 7 s por padrão; cada fase de 1 a 20 s,
soma até 30 s. São limites de busca; preparação, modelagem, validação e
serialização acrescentam custo. Uma avaliação em curso pode ultrapassar o
prazo do AG. O solver também pode exceder ligeiramente seu orçamento.

Veja [medições e limites da evidência](../docs/planning-validation.md) e os
[resultados por semente](../docs/examples/planning-benchmark.json).
A suíte inclui oráculo independente de ordens por máquina em instâncias de
até oito operações, invariantes gerados por sementes e certificação real.

Todas as unidades/máquinas estão disponíveis em zero, tempos são determinísticos,
buffers ilimitados e transporte/setup instantâneos. Não há reserva entre ordens,
persistência de planos nem execução física. A implementação segue a spec aprovada;
a [ADR-006](../docs/adr/0006-ag-cpsat-production-planning.md) continua **Proposta**.
