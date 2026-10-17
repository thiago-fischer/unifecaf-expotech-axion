# Validação da SPEC-0005 — 17/10/2026

Núcleo `axion_optimizer` 0.1.0, OR-Tools 9.15.6755, Python 3.12.13,
Windows 11 (10.0.26200), processador AMD64 Family 25 Model 33 Stepping 2,
16 CPUs lógicas. O relatório registra identificação do ambiente; não identifica
modelo comercial nem estabelece desempenho em outro equipamento.

## Qualidade e custo

Execução real de 30 buscas, seis entradas e cinco sementes (0–4), com perfil
AG 40/80, orçamento AG 3 s e CP-SAT 7 s, um worker por solver e gaps zero.
[Dados completos por semente](examples/planning-benchmark.json), incluindo
referências, melhor inicial/final do AG, tempos, gaps e proveniência.

| Entrada | Makespan melhor/média/pior (s) | Tempo médio/máximo (s) | Prova | Ganho médio sobre referência | Gap médio |
|---|---:|---:|---:|---:|---:|
| Histórico 1/1/1 | 65 / 65 / 65 | 0,03 / 0,03 | 5/5 | 0% | 0% |
| Histórico 3/2/4 | 175 / 175 / 175 | 0,17 / 0,17 | 5/5 | 0% | 0% |
| Receitas heterogêneas com revisitas | 110 / 110 / 110 | 0,20 / 0,22 | 5/5 | 19,12% | 0% |
| 100 unidades / 1.000 operações / 50 máquinas | 479 / 493,2 / 515 | 10,07 / 10,08 | 0/5 | 11,13% | 28,99% |
| Horizonte 1.000.000.000 s | 1e9 / 1e9 / 1e9 | <0,01 / 0,01 | 5/5 | 0% | 0% |
| 100 unidades / 1.000 operações com revisitas | 907 / 907 / 907 | 3,48 / 3,59 | 5/5 | 0% | 0% |

As referências já atingiram 65 s e 175 s; esses resultados não são atribuídos
à evolução. Nas receitas heterogêneas, o AG melhorou o melhor inicial em 2/5
sementes e o certificador não acrescentou melhoria. Na fronteira com 50 máquinas,
o AG evoluiu em 5/5 e o CP-SAT melhorou o AG em 5/5; essas melhorias adicionais
têm origem `cp_sat`. Ausência de prova nessa fronteira é preservada na qualidade,
mesmo com melhoria observada. O gap é incerteza sobre o ótimo, não erro medido.

O pico cumulativo de memória residente do processo, incluindo alocações nativas,
foi **107,42 MiB**. Cada execução registra esse pico cumulativo; não é memória
isolada de cada caso nem diferença de alocação por fase. Os limites iniciais
foram mantidos com essa evidência, sem aumento. Há apenas cinco sementes por
entrada; não se conclui prova ou desempenho garantido para toda entrada aceita.

Maior tempo de AG observado: 3,032 s (excedente de 0,032 s). Maior fase de
certificação: 7,032 s (inclui modelagem; excedente de 0,032 s). O prazo do AG
é conferido entre avaliações, com duas referências obrigatórias e possível
excedente de uma avaliação. O CP-SAT controla seu tempo de busca, não a
preparação do modelo Python. Os valores são observados, não tolerâncias garantidas.

## Impacto nas demais rotas

[Medição HTTP](examples/planning-http-benchmark.json) com TestClient, banco SQLite
temporário por migrations reais e uma busca real de 1.000 operações/50 máquinas.
`GET /machines`: 20 amostras sem busca (média 0,00235 s; máximo 0,016 s),
37 durante a busca (média 0,03457 s; máximo 0,500 s). A segunda requisição de
planejamento retornou 503 em 1,188 s; a principal terminou 409 sem prova.
Há contenção de CPU/GIL na fase Python e custo de validar o snapshot antes de
rejeitar concorrência. O bloqueio não cria fila de buscas nem mantém transação.

Essa é medição local em processo, sem rede externa ou carga de múltiplos clientes.
Não representa teste de carga de produção. Mais processos multiplicam buscas
e memória; precisam de avaliação própria. Os orçamentos não prometem latência
HTTP total. O controle local libera a trava em sucesso e falha.

## Cobertura e reprodução

Validação local concluída: **255 testes do backend e 56 do núcleo passaram**,
Ruff lint/formatação dos dois módulos passaram e `git diff --check` passou.
O núcleo também foi instalado e testado pelo próprio lockfile. Uma instalação
adicional em ambiente virtual vazio, fora do repositório, instalou os 39 pacotes
do backend pelo lockfile e executou o planejador real (ótimo de 30 s) e o OpenAPI.
O log de CI no PR registra a verificação Linux após publicação da branch.

Testes cobrem contratos HTTP e schemas estritos, catálogo personalizado, nomes
repetidos, IDs esparsos, paralelismo, quantidades, receitas heterogêneas/revisitas,
lacunas, permutações OX/swap, RNG local e reprodução por gerações fixas.
Um oráculo enumera ordens por máquina, elimina ciclos com precedências e calcula
caminhos em DAG para conferir instâncias pequenas de até oito operações;
não se limita ao espaço do decodificador. Estados do solver e arredondamento
são controlados em testes, além da integração real de OR-Tools.

Há adulteração controlada de planos/métricas, limites antes da expansão,
503 entre instâncias da API, devolução da conexão antes da busca, proibição de
SQL durante busca, liberação após falhas, ausência de novas tabelas ou alterações
nos cadastros e validação do exemplo documental contra schema e regras.

Comandos, a partir de `backend/`:

```powershell
uv sync --locked --python 3.12
uv run --locked pytest -q
uv run --locked pytest -q ../optimizer/tests
uv run --locked ruff check . ../optimizer
uv run --locked ruff format --check . ../optimizer
uv run --locked python -m axion_optimizer.experiments --output ../docs/examples/planning-benchmark.json
uv run --locked python -m scripts.measure_planning --output ../docs/examples/planning-http-benchmark.json
```

Os dois últimos comandos sobrescrevem os relatórios e dependem do relógio;
não se exigem barras idênticas sob timeout. A CI instala dependências pelo
lockfile, executa suítes/lint/formatação e valida o pacote isolado pelo seu
próprio lockfile. Veja também os READMEs de [backend](../backend/README.md)
e [optimizer](../optimizer/README.md).

Validação exclusivamente em software: não comprova funcionamento em hardware,
transporte da mesa ou restrições físicas omitidas por `job_shop_v1`.
A revisão de outro integrante e a aceitação formal da ADR-006 permanecem
pendentes; não houve merge nesta validação.
