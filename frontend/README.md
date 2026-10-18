# Frontend do Axion

Interface local em português implementada em React conforme a
[SPEC-0006](../docs/specs/0006-react-frontend.md) e a
[issue #10](https://github.com/thiago-fischer/unifecaf-expotech-axion/issues/10).
Permite cadastrar, listar e consultar máquinas, produtos com receitas e ordens,
além de calcular o planejamento transitório em software. Não inicia produção
física. Autenticação, cloud, telemetria e persistência de planos continuam fora
desta entrega.

## Instalação

Requisitos: Node.js **24.x**, npm e o monorepo completo. As versões exatas estão
em `package.json` e `package-lock.json`; use `npm ci` para reproduzir a instalação.

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
```

No Linux/macOS, use `cp .env.example .env`. O arquivo é opcional se o backend
estiver em `http://127.0.0.1:8000`.

## Execução local

Prepare as dependências, o banco por Alembic e inicie a API conforme o
[README do backend](../backend/README.md). Em outro terminal, nesta pasta:

```powershell
npm run dev
```

Abra [Axion local](http://127.0.0.1:5173). O processo escuta somente em
`127.0.0.1`; encerre com `Ctrl+C`.

`AXION_API_TARGET` configura o endereço da API no **proxy do Vite**. O navegador
sempre chama `/api` na mesma origem da interface; o proxy remove esse prefixo e
encaminha a requisição, inclusive status e `Retry-After`. Reinicie o Vite ao
alterar a variável. Ela também pode ser definida no ambiente do processo.
Não foi necessário modificar CORS nem rotas do backend. Não inclua credenciais:
variáveis de configuração do cliente não são um local seguro para segredos.

```powershell
$env:AXION_API_TARGET = 'http://127.0.0.1:8000'
npm run dev
```

O timeout é de 15 s para catálogos e de 60 s para planejamento no cliente;
o proxy usa 60 s. Busca, preparação e serialização compõem a latência total.
Timeout no navegador não garante cancelamento do servidor. O fluxo local foi
validado; 60 s não é garantia de resposta para todas as ordens e máquinas.

## Fluxo

1. Cadastre uma máquina ou utilize uma existente.
2. Crie um produto com etapas e tempos inteiros positivos em segundos. Etapas
   podem revisitar a mesma máquina; a sequência é gerada pela posição visual.
3. Crie uma ordem selecionando produtos distintos e quantidades inteiras positivas.
4. Consulte a ordem e acesse seu planejamento, ou selecione-a na área correspondente.

O padrão exige prova de ótimo. A opção “Permitir resultado viável sem prova de
ótimo” envia `allow_feasible`. `409 optimality_not_proven` mostra o candidato em
`result` como viável sem prova, sem mudar a política ou repetir a requisição.
O resumo mostra tempo total, prova e origem do plano; a tabela usa os nomes do
snapshot. As unidades são lógicas e os tempos relativos ao início do plano.
O resultado se perde ao sair da área ou recarregar a página.

Em `503 planning_busy`, o botão aguarda `Retry-After` antes de permitir nova
tentativa manual. Violações `422` mostram campo, valor e limite. Formulários
preservam o preenchimento em falhas. Se um cadastro perder a confirmação por
problema de conexão, confira a lista antes de reenviar para evitar duplicação.
Listas podem ser atualizadas manualmente; não há atualização em tempo real.

## Validação

```powershell
npm run check
npm run format:check
npm test
npm run build
```

`check` verifica tipos; `format:check` confere formatação; `test` executa Vitest
e React Testing Library em jsdom. Não foi adicionado linter separado.
`npm run format` aplica a formatação.

Para teste de navegador com API real:

```powershell
cd ../backend
uv sync --locked --python 3.12
cd ../frontend
npx playwright install chromium
npm run test:e2e
```

O Playwright inicia a API em `127.0.0.1:8765` e o Vite em `127.0.0.1:5174`.
Essas portas devem estar livres; servidores existentes não são reutilizados.
O script `scripts/serve_test_api.py` cria um SQLite temporário fora do repositório
e aplica as migrations reais. Não utiliza o banco de desenvolvimento.
Em Linux CI, use `npx playwright install --with-deps chromium`.

O teste percorre cadastro → consulta → planejamento, incluindo nomes repetidos,
revisita à máquina, uso dos IDs retornados, validação contra o resultado da API,
teclado e viewport de 390 px. Screenshots ficam em `test-results/` (ignorado).
Os testes controlados cobrem respostas sem prova, limites, ocupação, falhas de
rede, timeout e descarte de resultado antigo sem depender de tempo de busca.
Essa validação é em software, sem hardware real.

## Build e prévia

```powershell
npm run build
npm run preview
```

Prévia local em [127.0.0.1:4173](http://127.0.0.1:4173), com o mesmo proxy.
`dist/` contém arquivos estáticos; o proxy do Vite não faz parte desses arquivos.
Servir esse build em outro ambiente exigirá configurar o encaminhamento de
`/api`, assunto fora do escopo desta entrega.

## Escolhas

React com TypeScript, Vite, CSS, `fetch` e hooks, sem roteador ou biblioteca de
estado adicional. [ADR-007](../docs/adr/0007-react-frontend.md) registra motivos
e consequências. Backend, contratos e migrations foram preservados.
Referências das ferramentas: [proxy do Vite](https://vite.dev/config/server-options#server-proxy)
e [ambiente de testes do Vitest](https://vitest.dev/guide/environment.html).
