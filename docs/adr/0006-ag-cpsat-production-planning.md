# ADR-006 — AG obrigatório com verificação e certificação CP-SAT

- Status: Proposta
- Data: 17/10/2026
- Relacionada: [SPEC-0005](../specs/0005-production-planning.md)

## Contexto

O [estudo](../estudo-otimizacao-producao.md) recomenda Algoritmo Genético
com elitismo para minimizar makespan em job shop. O responsável confirmou
em 17/10/2026 que o AG é obrigatório por exigência acadêmica e que CP-SAT deve
verificar ou certificar a solução. Também exige produtos e máquinas criados
pelo usuário e saída compatível com Gantt por máquina.

Uma meta-heurística isolada não comprova que inexiste solução melhor. A
enumeração de cromossomos de um decodificador restrito também não prova o
ótimo do espaço completo de cronogramas. O problema exige separar validade,
qualidade observada e prova de otimalidade dentro do modelo adotado.

## Decisão proposta

Manter o AG como etapa obrigatória, precedido por referências determinísticas,
e validar seu resultado por um componente independente. Usar CP-SAT do
OR-Tools em Python para buscar no modelo completo e certificar o makespan,
com orçamento limitado e tolerâncias de gap zero. Aproveitar melhorias do
certificador e informar sua autoria, preservando os resultados próprios do AG.

Somente classificar como ótimo quando houver prova: solver com ótimo exato
ou limite inferior válido igual ao makespan. Se o orçamento acabar sem prova,
retornar plano viável explicitamente identificado. No contrato padrão, tratar
a falta de prova como requisito não atendido (`409` com candidato); permitir
resposta exploratória `200` apenas por opção explícita do cliente.

Receitas e máquinas são dados do snapshot; não haverá catálogo fixo no núcleo.
Cada unidade é um job; cada etapa tem máquina fixa e duração definida pelo
usuário. "Máquina fixa por etapa" não significa catálogo de receitas fixo.
Separar núcleo Python `optimizer/` da integração HTTP/ORM, seguindo as ADRs
aceitas. Persistência de planos e restrições de transporte ficam fora da
primeira entrega, com hipóteses declaradas e sem autorização de execução física.

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Apenas AG | Mantém a finalidade acadêmica, mas não oferece prova geral do mínimo |
| Apenas CP-SAT | Pode provar o ótimo, porém não atende à obrigatoriedade acadêmica do AG |
| AG e CP-SAT somente em testes | Útil para avaliar o AG, mas não certifica uma entrada nova criada pelo usuário |
| Enumeração completa em produção | Adequada apenas como oráculo em instâncias muito pequenas |
| AG com multa para planos inválidos | Não substitui construção válida e validador independente |

## Consequências

- Permite avaliar o aprendizado acadêmico e informar honestamente a qualidade
  de cada resposta para novas receitas.
- Preserva cronogramas melhores encontrados pelo certificador sem atribuir
  indevidamente esses resultados à evolução do AG.
- Acrescenta dependência OR-Tools, custos de instalação e cálculo; versão,
  compatibilidade, empacotamento e desempenho devem ser validados na implementação.
- Não promete tempo limitado para comprovar o ótimo em qualquer instância;
  requer limites e política explícita para resposta sem prova.
- A prova se refere ao modelo simplificado, sem transporte e buffers finitos.

## Estado e revisão

Esta ADR registra uma proposta técnica motivada pelo requisito do responsável;
não altera o status das ADRs aceitas. A implementação da SPEC-0005 em
`optimizer/` e no backend foi realizada em 17/10/2026, com OR-Tools 9.15.6755
e dependência local explícita. Consulte os [resultados de validação](../planning-validation.md).
Implementar a spec aprovada não muda automaticamente o status desta ADR;
a aceitação formal continua pendente de revisão da equipe.
Revisar resultados em receitas variadas, custo da certificação e aderência à
avaliação acadêmica antes de aceitar. Reavaliar quando houver restrições físicas,
recursos alternativos, múltiplas ordens ou necessidade de execução assíncrona.

## Fontes primárias

- [Job shop no OR-Tools](https://developers.google.com/optimization/scheduling/job_shop):
  intervalos, precedência, exclusividade e objetivo makespan.
- [CP-SAT](https://developers.google.com/optimization/cp/cp_solver):
  distinção entre solução viável, ótimo comprovado e estados sem solução.
- [Limites de busca](https://developers.google.com/optimization/cp/cp_tasks):
  orçamento de execução do solver.

Fontes consultadas em 17/10/2026; a dependência foi instalada e fixada na
implementação da SPEC-0005, mantendo esta ADR como proposta.
