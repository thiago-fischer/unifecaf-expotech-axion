# SPEC-0006 — Interface web em React para a API local

> **Status:** Aprovada pelo responsável; implementada e validada localmente, aguardando revisão de outro integrante.
>
> **Data:** 17/10/2026
>
> **Issue:** [#10 — feat: criar frontend básico em React para utilizar a API do Axion](https://github.com/thiago-fischer/unifecaf-expotech-axion/issues/10)

## 1. Objetivo e contexto

Permitir que o usuário utilize a API local do Axion em português, sem depender
do Swagger: cadastrar máquinas, montar receitas de produtos, registrar ordens
e consultar o planejamento em software.

O backend já implementa esses contratos nas SPEC-0001, SPEC-0003, SPEC-0004
e SPEC-0005. O diretório `frontend/` não existia no momento do rascunho e foi
criado nesta implementação.
A implementação foi autorizada pelo responsável em 17/10/2026 após a aprovação deste rascunho. A interface não altera o comportamento da API.

React é requisito explícito da issue #10. Na redação do rascunho, a arquitetura e a visão geral ainda
descreviam a tecnologia do frontend como indefinida: essa diferença foi
resolvida na implementação, registrando a escolha na ADR-007 e atualizando os
documentos. A ADR-007 registra a aprovação do responsável; o PR ainda exige revisão. As ADRs 001 a 005
permanecem como referência; a ADR-006 de otimização continua **Proposta**,
embora o planejamento já esteja implementado conforme a SPEC-0005 aprovada.

## 2. Escopo

### Incluído

- Módulo `frontend/` separado do backend, em React, com componentes funcionais,
  hooks e navegação simples entre máquinas, produtos, ordens e planejamento.
- Listagem, cadastro e consulta individual de máquinas, produtos e ordens.
- Formulário de receita com adição e remoção de etapas.
- Solicitação explícita de planejamento para uma ordem existente.
- Resumo do resultado e tabela de operações, inclusive para candidatos sem prova.
- Configuração da API por ambiente e acesso pelo navegador em desenvolvimento.
- Estados de carregamento, vazio, sucesso, validação e falha de comunicação.
- Interface legível em desktop e telas menores, com navegação por teclado.
- Documentação dos comandos e validação da integração com a API real.

### Fora desta entrega

- Editar ou excluir cadastros, cancelar ordens ou oferecer ações sem rota na API.
- Autenticação, cloud, deploy, dashboard completo e Gantt interativo.
- Telemetria, Grafana, firmware, execução física, rastreabilidade física e
  validação final de unidades.
- Persistência de planos, fila de cálculo, execução assíncrona e novos
  algoritmos ou regras de otimização.

## 3. Fluxo e telas

Fluxo principal: **máquina → produto com receita → ordem → planejamento**.
Cadastros concluídos devem ficar disponíveis nas etapas seguintes da mesma
sessão, sem reiniciar a aplicação. Não pressupor dados iniciais.

| Área | Conteúdo e ações |
|---|---|
| Máquinas | Listar ID e nome; cadastrar nome; abrir consulta individual |
| Produtos | Listar ID e nome; cadastrar nome e etapas; consultar receita ordenada com máquina e duração |
| Ordens | Listar IDs e itens; criar com produtos e quantidades; consultar detalhe; acessar planejamento |
| Planejamento | Selecionar ordem, escolher política, solicitar cálculo e consultar resumo e operações |

As listagens devem buscar dados reais e oferecer atualização manual. Após
cadastro bem-sucedido, atualizar a lista e disponibilizar o registro retornado.
Usar IDs como identidade; nomes podem se repetir. Nos seletores, mostrar nome
e ID para distinguir registros. Na consulta de ordens, resolver nomes no catálogo
e preservar o ID como alternativa se a consulta complementar falhar.

Sem máquinas, explicar que é necessário cadastrar uma antes de criar uma receita,
com acesso à área correspondente. Aplicar o mesmo comportamento a produtos
necessários para ordens e ordens necessárias para planejamento.

### 3.1. Máquinas

- Nome obrigatório, com 1 a 100 caracteres após remover espaços das extremidades.
- Enviar somente `{ "name": "..." }`; ID é gerado pelo backend.
- A consulta mostra identidade cadastral, sem inventar estado operacional.

### 3.2. Produtos e receitas

- Nome com a mesma validação do cadastro de máquinas.
- Exigir ao menos uma etapa, com máquina existente e duração inteira positiva
  em segundos, no campo `processing_time_seconds`.
- A posição visual define `sequence`: recalcular de 1 a N após adicionar ou
  remover etapas, sem lacunas. Não é necessário implementar arrastar e soltar.
- Permitir revisitas à mesma máquina, inclusive em etapas consecutivas.
- Enviar somente `name` e `steps`, com `sequence`, `machine_id` e
  `processing_time_seconds` em cada etapa.
- Converter os valores dos campos em números JSON inteiros válidos antes de
  enviar; não truncar decimais nem transformar vazio em zero.

### 3.3. Ordens

- Exigir ao menos um item com produto existente e quantidade inteira positiva.
- Impedir produtos duplicados; uma quantidade representa a demanda daquele
  produto. Permitir adicionar e remover itens antes de enviar.
- Enviar somente `items`, com `product_id` e `quantity` em cada item.
- Explicar no sucesso: a ordem registra demanda, sem iniciar produção, reservar
  máquinas ou gerar planejamento automaticamente.

## 4. Integração HTTP

Manter rotas, schemas e regras existentes; a API continua sendo a autoridade
de validação. Não acessar banco ou módulo de otimização diretamente pelo frontend.

| Recurso | Método e rota | Sucesso |
|---|---|---|
| Máquinas | `GET /machines`, `GET /machines/{machine_id}` | `200` |
| Cadastro de máquina | `POST /machines` | `201` |
| Produtos | `GET /products`, `GET /products/{product_id}` | `200` |
| Cadastro de produto | `POST /products` | `201` |
| Ordens | `GET /orders`, `GET /orders/{order_id}` | `200` |
| Cadastro de ordem | `POST /orders` | `201` |
| Planejamento | `POST /orders/{order_id}/plan` | `200` ou candidato em `409` |

Listagens retornam arrays, inclusive `[]`. Consultas inexistentes retornam
`404`; mostrar mensagem compreensível e permitir voltar à listagem.
Não exigir nomes únicos, IDs consecutivos ou catálogo fixo.

### 4.1. Requisição de planejamento

Usar os padrões da API, enviando `{}` na política padrão. Oferecer opção
desmarcada inicialmente, com rótulo equivalente a “Permitir resultado viável
sem prova de ótimo”. Ao marcar, enviar:

```json
{ "optimality_policy": "allow_feasible" }
```

Desmarcar restaura `require_proof`. Não mudar a política nem repetir o cálculo
automaticamente após um `409`. Os padrões atuais são 3 s para AG, 7 s para
certificação e semente 0; controles avançados desses parâmetros ficam fora
deste rascunho.

O cálculo é síncrono. Mostrar “Calculando planejamento” enquanto aguarda,
sem percentual fictício, desabilitando novo envio. Como proposta inicial,
usar timeout de 60 s no cliente e no proxy para planejamento, a validar no
ambiente local: o orçamento de busca não inclui toda a preparação e serialização
e não garante latência total. Distinguir timeout de conexão indisponível.
Abortar a espera do navegador não garante interrupção da busca no servidor.

### 4.2. Resultado

| Informação na interface | Campo de origem |
|---|---|
| Ordem consultada | `order_id` |
| Tempo total planejado, em segundos | `metrics.makespan_seconds` |
| Qualidade: ótimo ou viável | `quality` |
| Prova de ótimo: sim ou não | `optimality_proven` |
| Origem: Algoritmo Genético ou CP-SAT | `selected_source` |
| Método de prova | `proof.method` |
| Produto e máquina de cada operação | Nomes em `input_snapshot`, associados pelos IDs |
| Unidade lógica, etapa, início, fim e duração | `unit_id`, `step_sequence`, `start_seconds`, `end_seconds`, `duration_seconds` em `operations` |

Exibir uma linha por operação, preservando operações simultâneas e a ordem
recebida. Os tempos são relativos ao início do plano, em segundos, não horários
reais. A unidade é lógica no planejamento, sem equivaler à identificação de uma
peça física. Associar nomes exclusivamente ao snapshot desse resultado, sem
substituí-los por valores de consultas posteriores ao catálogo.

Mostrar aviso permanente junto ao resultado: “Planejamento em software; não
habilita execução física”. `execution_ready: false` não é falha do cálculo.
Explicar que a prova se refere ao modelo simplificado, sem transporte e setup.
Não oferecer botão para executar a ordem na maquete.

Resultados são transitórios. Uma nova solicitação substitui a visualização
anterior; ao trocar de ordem, limpar o resultado para evitar associação
incorreta. Descartar respostas atrasadas de uma seleção anterior. Recarregar
a página pode perder o plano, pois não há endpoint para recuperá-lo.

### 4.3. Tratamento de respostas e falhas

| Condição | Comportamento esperado |
|---|---|
| `200`, `quality: optimal` | Mostrar resultado e prova conforme os campos retornados |
| `200`, `quality: feasible` | Mostrar resultado viável, sem apresentar ótimo comprovado |
| `409`, `code: optimality_not_proven` | Ler `result` e mostrar candidato completo com destaque “Viável, sem prova de ótimo”; não indicar ordem inviável |
| `422`, `code: planning_limits_exceeded` | Mostrar cada violação de `violations`, com campo, valor atual e limite |
| `422` de validação | Tratar `detail` como texto ou lista de erros; associar campos por `loc` quando possível |
| `422` de referência ausente | Mostrar mensagem e IDs de `machine_ids` ou `product_ids`, quando presentes; permitir atualizar catálogo |
| `503`, `code: planning_busy` | Informar ocupação e respeitar `Retry-After` antes de habilitar nova tentativa manual |
| `404` | Informar recurso não encontrado e permitir selecionar outro registro |
| `500` e outros erros HTTP | Mostrar falha compreensível, sem expor detalhes internos ou tratar como lista vazia |
| Rede, timeout ou resposta ilegível | Distinguir falha de comunicação e permitir recuperação manual |

Não repetir POSTs automaticamente. Em falha de comunicação após cadastro,
informar que a confirmação não foi recebida e orientar conferir a lista antes
de reenviar: o servidor pode ter concluído a gravação. Preservar o formulário
nos erros sempre que possível. Não aplicar sucesso otimista antes da resposta.

## 5. Organização e decisões técnicas

React é requisito; as escolhas abaixo foram adotadas na implementação, conforme
a aprovação desta spec e a ADR-007. A revisão por outro integrante permanece pendente.

| Tema | Escolha e justificativa |
|---|---|
| Linguagem e desenvolvimento | TypeScript e Vite, para explicitar contratos e preparar execução/build de uma SPA local |
| Navegação | Navegação simples por áreas; escolher roteador somente se as telas exigirem URLs próprias |
| Estado e HTTP | Hooks e cliente HTTP centralizado com `fetch`; manter status, corpo e cabeçalhos disponíveis para os tratamentos previstos |
| Estilo | CSS responsivo, sem exigir biblioteca de componentes para o escopo básico |
| Integração local | Proxy de desenvolvimento para a API; evitar alteração no backend se essa opção atender ao fluxo |
| Testes | Vitest e React Testing Library para testar comportamentos e respostas controladas; Playwright para integração com API real |

Organização sugerida, a ajustar à implementação:

```text
frontend/
├── src/
│   ├── api/          # Cliente HTTP e contratos
│   ├── components/   # Elementos compartilhados pelas telas
│   ├── pages/        # Máquinas, produtos, ordens e planejamento
│   └── App.tsx
├── .env.example
├── package.json
└── README.md
```

Documentar a configuração da URL de destino da API por ambiente e distinguir
o endereço usado pelo proxy do caminho usado pelo navegador. Valores de
ambiente incluídos no bundle são públicos e não devem conter segredos.
Se acesso direto for necessário em vez do proxy, configurar CORS somente para
origens locais necessárias e expor `Retry-After` para leitura pelo navegador.
Documentar e testar a opção adotada; não usar liberação indiscriminada de origens.

Na implementação, registrar React e as escolhas efetivas em uma nova ADR com
status explícito, preservando a numeração disponível naquele momento. Atualizar
arquitetura e visão geral sem declarar a interface pronta antes da validação.
Não são previstas migrations, novas rotas nem mudanças de regras de negócio.

## 6. Critérios de aceite

Itens validados localmente conforme as evidências da seção 8. CI e revisão do PR permanecem pendentes.

- [x] CA-01: Módulo React separado, em português, com navegação entre as quatro áreas.
- [x] CA-02: Máquinas permitem listar, cadastrar e consultar com IDs reais.
- [x] CA-03: Produtos permitem listar, cadastrar e consultar receitas; formulário
  adiciona/remove etapas, gera sequências consecutivas e aceita revisitas.
- [x] CA-04: Ordens permitem listar, criar e consultar; impedem duplicatas e
  exigem quantidades inteiras positivas, sem anunciar início de execução.
- [x] CA-05: Fluxo completo funciona com API real e cadastros da mesma sessão,
  incluindo nomes repetidos e IDs sem sequência fixa.
- [x] CA-06: Listas vazias, carregamento, sucesso, `404`, validação e falhas de
  comunicação têm estados claros; envios simultâneos do mesmo formulário são bloqueados.
- [x] CA-07: Política padrão exige prova; `allow_feasible` depende de opção explícita.
- [x] CA-08: Planejamento trata `200 optimal`, `200 feasible`, `409` com `result`,
  `422`, `503` com `Retry-After`, erro de servidor e falha de conexão/timeout.
- [x] CA-09: Resumo e tabela exibem os campos previstos, nomes do snapshot e
  aviso sobre execução física; troca de ordem não mostra resultado anterior.
- [x] CA-10: Interface legível em desktop e telas menores, com campos rotulados,
  foco visível, navegação por teclado e mensagens de estado acessíveis.
- [x] CA-11: Build e verificações definidas no módulo passam; testes cobrem os
  tratamentos de planejamento com respostas controladas.
- [x] CA-12: README documenta instalação, execução, configuração da API e
  validação; ADR e documentação refletem as escolhas efetivas.

## 7. Plano de validação e entrega

1. Definir e documentar comandos de instalação, desenvolvimento, build,
   verificação de tipos/lint e testes no `frontend/README.md`, com lockfile.
2. Testar formulários e integração HTTP com respostas controladas: distinção
   entre `200` e `409`, leitura de `result`, limites em `422`, espera de
   `Retry-After`, falha de rede e prevenção de envios duplicados.
3. Validar manualmente com API real e banco descartável preparado por Alembic:
   máquina nova → receita com revisita → ordem → planejamento. Conferir
   quantidades, nomes e tabela contra o retorno da API.
4. Verificar telas menores, teclado e estados vazios/erros. Para falta de prova,
   preferir respostas controladas nos testes, sem depender do tempo aleatório da busca.
5. Executar build e verificações do frontend. Se o backend for alterado para
   integração, executar suas verificações pertinentes e documentar o efeito.
6. Registrar comandos executados, resultados e limitações no PR; obter revisão
   de outro integrante antes do merge, conforme CONTRIBUTING.md.

Dependências instaladas, `node_modules/`, caches e saídas de build são ignorados
pelo Git. A validação é local e em software, sem comprovação em hardware real.

## 8. Implementação e validação

Aprovação da spec e autorização de implementação recebidas do responsável em
17/10/2026. Implementados React, TypeScript, Vite, proxy local, formulários,
consultas e planejamento. A ADR-007 registra as escolhas; arquitetura, visão
geral e READMEs foram atualizados. Backend e migrations foram preservados.

Validações locais executadas:

- `npm run check`, `npm run format:check` e `npm run build`: aprovados.
- `npm test`: 20 testes aprovados, cobrindo contrato HTTP, planejamento e formulários.
- `uv run --locked pytest -q` em `backend/`: 255 testes aprovados, com dois
  avisos de depreciação das dependências de teste existentes.
- `uv run --locked pytest -q ../optimizer/tests`: 56 testes aprovados.
- Ruff sobre `frontend/scripts/`: lint e formatação aprovados.
- `npm run test:e2e`: 1 teste aprovado em Chromium com API real, Alembic e SQLite
  descartável; fluxo completo com nomes repetidos, IDs retornados e revisita.
  Ordem de duas unidades com etapas de 4 s e 7 s: quatro operações e makespan de 22 s.
- Capturas de desktop e viewport de 390 px inspecionadas; navegação por teclado
  e ausência de transbordamento da página verificadas no teste de navegador.
- Pipeline de frontend adicionado para repetir tipos, formatação, testes,
  build e integração com API real no GitHub Actions.

O timeout de 60 s foi configurado no cliente e no proxy; não é garantia de
latência em todas as entradas. Não houve validação em hardware real.
Pendências: execução da CI e revisão do PR por outro integrante antes do merge.

## 9. Referências

- [Issue #10](https://github.com/thiago-fischer/unifecaf-expotech-axion/issues/10).
- [Contribuição](../../CONTRIBUTING.md), [arquitetura](../architecture.md) e
  [visão geral](../visao-geral.md).
- [SPEC-0001 — Máquinas](0001-backend-machines.md).
- [SPEC-0003 — Produtos](0003-backend-products.md).
- [SPEC-0004 — Ordens](0004-production-orders.md).
- [SPEC-0005 — Planejamento](0005-production-planning.md).
- [README do backend](../../backend/README.md) e
  [evidências do planejamento](../planning-validation.md).
- [ADR-003 — Monorepo](../adr/0003-monorepo.md),
  [ADR-004 — Camadas](../adr/0004-arquitetura-em-camadas-backend.md),
  [ADR-005 — Persistência](../adr/0005-sqlalchemy-pydantic-alembic.md) e
  [ADR-006 — Otimização, proposta](../adr/0006-ag-cpsat-production-planning.md).
