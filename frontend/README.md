# Frontend do Axion

Interface local em React, organizada em **Produção**, **Planejamento**,
**Maquete virtual** e **Sobre**. A interface consulta o catálogo de máquinas,
cadastra produtos e ordens, mostra o Gantt e acompanha a execução no controlador
simulado. A guia Sobre explica o projeto, o fluxo e a otimização.

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

1. Em **Produção**, consulte as máquinas cadastradas e, se precisar, abra **Novo produto**.
   Uma receita tem etapas em sequência, com máquina e duração em segundos.
   Etapas podem revisitar a mesma máquina. A interface oferece consulta às máquinas.
2. Crie uma ordem de produção com 1 a 10 produtos distintos e quantidades inteiras
   positivas. O contador mostra quantas linhas a ordem contém e a API valida o mesmo limite.
3. Selecione a ordem em **Planejamento** e clique em **Calcular OP** para ver o Gantt.
4. Em **Maquete virtual**, selecione a ordem e acompanhe o processamento simulado.
   O controlador aceita até 10 peças no total por execução.

O padrão exige prova de ótimo. A opção “Permitir resultado viável sem prova de
ótimo” envia `allow_feasible`. `409 optimality_not_proven` mostra o candidato em
`result` como viável sem prova, sem mudar a política ou repetir a requisição.
O resumo mostra tempo total, prova e origem do plano. O Gantt exibe uma linha
por máquina, barras proporcionais ao início e à duração e cores por produto,
usando nomes do snapshot. Passe o cursor ou use Tab nas barras para consultar
unidade, etapa e tempos. Em telas menores, o gráfico tem rolagem horizontal.
A tabela detalhada começa recolhida: clique em “Tabela de operações” ou use
Enter/Espaço no controle para expandir e recolher. As unidades são lógicas e
os tempos relativos ao início do plano.
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
cd ..
docker compose up -d database
cd backend
uv sync --locked --python 3.12
cd ../frontend
npx playwright install chromium
npm run test:e2e
```

O Playwright inicia a API em `127.0.0.1:8765`, o controlador simulado em
`127.0.0.1:8766` (com as dependências do backend) e o Vite em `127.0.0.1:5174`.
Essas portas precisam estar livres.
O script `scripts/serve_test_api.py` recria o banco PostgreSQL descartável
`axion_frontend_e2e`, aplica as migrations reais e tenta removê-lo ao encerrar.
Como o Playwright pode finalizar o servidor à força, a próxima execução também
remove qualquer banco E2E remanescente antes de recriá-lo. O script usa
`AXION_TEST_ADMIN_DATABASE_URL` quando definida e não acessa o banco de
desenvolvimento.
Em Linux CI, use `npx playwright install --with-deps chromium`.

Os testes percorrem cadastro → consulta → planejamento, incluindo revisita à máquina,
uso dos IDs retornados, validação contra o resultado da API,
teclado e viewport de 390 px. Também conferem o Gantt com três produtos, três
máquinas e 14 operações, além da expansão e recolhimento da tabela pelo teclado.
Screenshots ficam em `test-results/` (ignorado).
Os testes controlados cobrem respostas sem prova, limites, ocupação, falhas de
rede, timeout e descarte de resultado antigo sem depender de tempo de busca.
A maquete é validada em navegador com execução e restauração no controlador
simulado, incluindo acompanhamento textual sem WebGL.

## Build e prévia

```powershell
npm run build
npm run preview
```

Para construir a imagem e iniciar o projeto completo, execute na raiz do
monorepo:

```powershell
docker compose up --build
```

Prévia local em [127.0.0.1:4173](http://127.0.0.1:4173), com o mesmo proxy.
`dist/` contém arquivos estáticos; o proxy do Vite não faz parte desses arquivos.
Ao iniciar a aplicação completa pelo Compose da raiz, o Nginx da imagem do
frontend serve esse diretório e encaminha `/api` para o serviço `backend`.
Outros ambientes ainda precisam fornecer um encaminhamento equivalente.

## Escolhas

React com TypeScript, Vite, CSS, `fetch` e hooks, sem roteador ou biblioteca de
estado adicional. [ADR-007](../docs/adr/0007-react-frontend.md) registra motivos
e consequências.
Referências das ferramentas: [proxy do Vite](https://vite.dev/config/server-options#server-proxy)
e [ambiente de testes do Vitest](https://vitest.dev/guide/environment.html).

## Maquete virtual

A cena Three.js acompanha exclusivamente o estado do controlador simulado via
backend. Inicie os serviços com o Compose da raiz ou configure o backend com
[`AXION_CONTROLLER_URL`](../backend/README.md#executar-a-ordem-na-maquete-simulada)
apontando para o [controlador](../controller/README.md).

Selecione uma ordem em **Maquete virtual**. Abra **Associação de estações** para
revisar o vínculo entre as máquinas da receita e M1, M2 e M3. **Iniciar simulação**
faz o servidor calcular o plano da ordem e coordenar a execução, que continua
mesmo se você sair da guia.

Acompanhe a posição da mesa, RFIDs, estados das máquinas e validação das peças.
Arraste a cena para orbitar e role para aproximar. **Estações e peças** mostra os
estados também em texto. **Movimento reduzido** limita as mudanças de posição
às atualizações do servidor. **Velocidade** ajusta o relógio simulado entre 0,5× e
4×. Ao terminar, **Restaurar maquete** repõe as peças e volta para 1×.

A cena é carregada ao abrir a guia. O build pode emitir aviso sobre o tamanho
do módulo 3D. O contrato e o fluxo do controlador estão na
[ADR-011](../docs/adr/0011-api-controlador-maquete.md).
