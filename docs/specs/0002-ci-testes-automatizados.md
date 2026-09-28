# SPEC-0002 — CI inicial com testes automatizados no GitHub Actions

> **Status:** Aprovada para implementação
>
> **Data:** 27/09/2026
>
> **Aprovação do escopo:** 27/09/2026, pelo responsável solicitante, nesta revisão
>
> **Implementação:** Workflow e documentação implementados e validados localmente;
> execução no GitHub Actions pendente nesta revisão

## 1. Objetivo

Criar a primeira etapa da pipeline de CI/CD do Axion no GitHub Actions,
automatizando a execução da suíte de testes existente do backend em Pull Requests
e na branch `main`.

Esta entrega trata somente de integração contínua (CI). Ela cria uma base segura
e reproduzível para validações futuras, mas não realiza entrega ou implantação
contínua (CD), pois a plataforma de cloud e a estratégia de deploy permanecem em
aberto na visão geral do projeto.

## 2. Contexto atual

O backend já possui:

- Python 3.12 ou superior;
- dependências declaradas em `backend/pyproject.toml`;
- versões resolvidas em `backend/uv.lock`;
- pytest no grupo de dependências de desenvolvimento;
- testes automatizados executáveis localmente;
- instruções locais de validação em `backend/README.md`.

Ainda não existe um diretório `.github/` nem um workflow versionado. A suíte atual
é executada com pytest e verifica regras do service, API, persistência SQLite,
migrations Alembic e inicialização da aplicação. Por exercitar a colaboração
entre esses componentes, ela é predominantemente uma suíte de integração, embora
também cubra comportamentos de regras de negócio.

## 3. Referências e decisões existentes

- [Visão geral](../visao-geral.md): cloud e estratégia de CI/CD ainda em aberto.
- [Arquitetura](../architecture.md): componentes e tecnologias do sistema.
- [ADR-001](../adr/0001-python-fastapi.md): Python e FastAPI no backend.
- [ADR-003](../adr/0003-monorepo.md): componentes isolados e validações por módulo.
- [ADR-004](../adr/0004-arquitetura-em-camadas-backend.md): separação de
  responsabilidades do backend.
- [SPEC-0001](0001-backend-machines.md): backend atual e validações existentes.
- [Guia de contribuição](../../CONTRIBUTING.md): Pull Requests, revisão e CI/CD.
- [README do backend](../../backend/README.md): comandos reproduzíveis com `uv`.
- [Sintaxe de workflows do GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax):
  eventos, permissões e concorrência.
- [Uso seguro do GitHub Actions](https://docs.github.com/en/actions/reference/security/secure-use):
  fixação de actions por SHA completo e redução de permissões.
- [Integração do uv com GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/):
  instalação, lockfile e cache no runner.

A escolha do GitHub Actions está prevista no guia de contribuição e é aprovada
para esta entrega. Esta spec não aprova provedor de cloud, ambiente de execução
da aplicação, estratégia de release ou mecanismo de deploy.

Como referências de implementação, devem ser consultadas a documentação oficial
de sintaxe e segurança do GitHub Actions e a integração oficial do `uv` com
GitHub Actions. A implementação deve fixar ações externas por SHA completo e
registrar em comentário a versão correspondente.

## 4. Escopo

### Incluído

- Criar um workflow em `.github/workflows/` para os testes automatizados do backend.
- Executar o workflow em Pull Requests destinados à `main`.
- Executar o workflow após pushes na `main`.
- Disponibilizar execução manual por `workflow_dispatch` para diagnóstico.
- Preparar um runner Linux hospedado pelo GitHub com Python 3.12.
- Instalar as dependências do backend de forma reproduzível com `uv` e
  `backend/uv.lock`.
- Executar a suíte completa já existente com pytest, sem alterar o comportamento
  funcional da aplicação.
- Cancelar execuções antigas do mesmo Pull Request quando um novo commit chegar.
- Aplicar permissões mínimas ao `GITHUB_TOKEN` e não utilizar segredos.
- Documentar no README do backend o comando local equivalente ao executado na CI.
- Documentar o nome estável da verificação para futura proteção da `main`.

### Fora desta entrega

- Deploy em qualquer ambiente.
- Publicação de pacote, imagem de contêiner, release ou artefato de produção.
- Escolha de AWS, Azure, Google Cloud ou outro provedor.
- Uso de credenciais, secrets, OIDC ou ambientes protegidos do GitHub.
- Criação de uma suíte unitária separada, mocks ou doubles apenas para satisfazer
  uma classificação de testes.
- Reorganização obrigatória dos testes em diretórios por categoria.
- Marcadores pytest para distinguir testes unitários e de integração.
- Testes end-to-end, testes de hardware e comunicação com a maquete.
- Cobertura mínima obrigatória e publicação de relatório de cobertura.
- Lint, formatação, análise estática e análise de vulnerabilidades na pipeline.
- Matriz com múltiplos sistemas operacionais ou versões de Python.
- Configuração automática das regras de proteção da branch no GitHub.

Os itens fora do escopo podem virar etapas posteriores da CI/CD. Sua ausência
nesta primeira entrega não significa que estejam descartados.

## 5. Estratégia de testes desta entrega

A CI executará a suíte automatizada completa existente. Não será criada uma
separação obrigatória entre testes unitários e de integração nesta etapa, pois a
suíte atual é pequena, rápida e cobre os principais fluxos do backend.

Essa decisão evita reorganização de arquivos, marcadores, mocks e duplicação de
cenários sem benefício proporcional para o estágio atual do projeto. Ela não
reduz o valor dos testes existentes: o uso de SQLite temporário, migrations reais,
`TestClient` e subprocesso verifica integrações importantes do backend sem acessar
o banco de desenvolvimento ou depender da maquete.

Testes unitários isolados poderão ser adicionados quando surgirem regras complexas
que justifiquem essa separação, especialmente no módulo de otimização, em cálculos
de programação da produção ou em outras funções puras. Isso será uma evolução
orientada por necessidade concreta, não um requisito desta spec.

A pipeline terá como contrato o mesmo comando completo já documentado para uso
local:

```powershell
uv run --locked pytest -q
```

## 6. Comportamento do workflow

O workflow deve possuir nome e job estáveis para que a verificação possa ser
exigida posteriormente nas regras de proteção da `main`.

| Item | Definição |
|---|---|
| Arquivo sugerido | `.github/workflows/backend-tests.yml` |
| Nome do workflow | `Backend CI` |
| Nome do job/check | `Tests (Python 3.12)` |
| Runner | `ubuntu-latest` |
| Diretório de trabalho | `backend/` |
| Python | `3.12` |
| Gerenciador | `uv` |
| Instalação | sincronização validada por `uv.lock` |
| Testes | `uv run --locked pytest -q` |
| Token | somente leitura de conteúdo; demais permissões desabilitadas |
| Segredos | nenhum |

### 6.1. Eventos

O workflow deve responder a:

- `pull_request` com destino à `main`;
- `push` na `main`;
- `workflow_dispatch`.

Nesta primeira versão, o workflow será executado em todos os Pull Requests para
que seu check tenha resultado previsível, inclusive quando for configurado como
obrigatório. Filtros por caminho podem ser introduzidos quando outros módulos
tiverem pipelines próprias e houver uma estratégia que não deixe checks
obrigatórios permanentemente pendentes.

### 6.2. Concorrência

Execuções do mesmo workflow e da mesma referência devem compartilhar um grupo de
concorrência. Uma execução nova deve cancelar a anterior ainda em andamento,
evitando consumo para validar commits que já foram substituídos.

O identificador do workflow deve fazer parte do grupo para não cancelar, no
futuro, workflows independentes do frontend, firmware ou otimização.

### 6.3. Ambiente e dependências

- O job deve começar em runner limpo e não depender de `.venv` versionado.
- O checkout não deve manter credenciais além do necessário.
- A versão do Python deve ser explícita e corresponder à versão mínima suportada.
- O `uv` deve usar cache baseado nos arquivos de lock/configuração do backend.
- A sincronização deve falhar se `uv.lock` estiver ausente ou desatualizado.
- O job não deve criar ou usar `backend/data/axion.db`.
- Nenhuma variável ou segredo de produção deve estar disponível ao teste.

As actions reutilizadas, incluindo checkout e preparação do `uv`, devem ser
fixadas por SHA completo verificado no repositório oficial. A atualização desses
SHAs deve ocorrer por Pull Request revisável.

## 7. Regras

| Código | Regra |
|---|---|
| RN-01 | Todo PR destinado à `main` deve produzir um resultado para o check de testes do backend. |
| RN-02 | Falha de instalação, lock inconsistente, ausência de testes coletados ou teste falho deve falhar o job. |
| RN-03 | O job não pode modificar arquivos versionados nem fazer commits no repositório. |
| RN-04 | O workflow não pode receber permissão de escrita nem acessar secrets. |
| RN-05 | A execução local documentada deve usar o mesmo lockfile e o mesmo comando completo de testes da CI. |
| RN-06 | A suíte deve usar recursos temporários e não pode acessar o banco de desenvolvimento, serviços externos ou hardware. |
| RN-07 | Os testes existentes não podem ser apagados ou substituídos apenas para reduzir o tempo da CI. |
| RN-08 | O nome do check só deve mudar junto com a documentação e a configuração de proteção da branch. |
| RN-09 | A pipeline deve validar código não confiável de PR com o evento `pull_request`, nunca com `pull_request_target`. |
| RN-10 | Falha ou cancelamento da CI não equivale a validação bem-sucedida. |

## 8. Segurança

Esta etapa executará código do próprio Pull Request. Por isso:

- usar `pull_request`, que mantém permissões restritas para contribuições externas;
- declarar explicitamente permissões mínimas do token;
- não fornecer secrets ao job;
- não usar scripts obtidos por download sem verificação;
- fixar actions externas por SHA completo, com a tag de versão em comentário;
- usar apenas actions oficiais do GitHub e do projeto `uv` nesta entrega;
- não executar deploy, publicação ou outro efeito externo no mesmo job;
- manter `persist-credentials: false` no checkout quando compatível com a action.

Uma futura etapa de CD deverá usar job e workflow separados, permissões próprias,
ambiente protegido e aprovação compatível com o risco do destino.

## 9. Critérios de aceite

Os critérios permanecem desmarcados até a implementação e a execução real no
GitHub Actions. Validação somente local não comprova os eventos ou permissões do
serviço hospedado.

- [ ] CA-01: O workflow é sintaticamente válido e aparece na aba Actions.
- [ ] CA-02: Um PR destinado à `main` inicia o check `Tests (Python 3.12)`.
- [ ] CA-03: Um push na `main` inicia o mesmo workflow.
- [ ] CA-04: A execução manual pode ser iniciada pela interface do GitHub.
- [ ] CA-05: Em um commit válido, o ambiente é preparado pelo lockfile e toda a
  suíte existente passa em runner Linux com Python 3.12.
- [ ] CA-06: Alterar intencionalmente um teste para falhar deixa o check vermelho
  e impede que a execução seja interpretada como sucesso.
- [ ] CA-07: Remover ou desatualizar o lockfile faz a etapa de sincronização falhar.
- [ ] CA-08: O comando local documentado executa a mesma suíte completa da CI.
- [ ] CA-09: A suíte usa somente bancos e arquivos temporários, sem alterar o banco
  de desenvolvimento, acessar serviços externos ou depender de hardware.
- [ ] CA-10: Os testes de API, service, migrations e inicialização existentes são
  coletados e executados no workflow.
- [ ] CA-11: O workflow declara permissões somente de leitura e não usa secrets.
- [ ] CA-12: As actions externas estão fixadas por SHA completo e identificadas
  por versão em comentário.
- [ ] CA-13: Dois commits sucessivos no mesmo PR cancelam a execução obsoleta sem
  cancelar workflows de outros módulos.
- [ ] CA-14: Um PR apenas de documentação também recebe conclusão do check, sem
  ficar indefinidamente pendente.
- [ ] CA-15: O workflow não altera arquivos versionados e o diretório de trabalho
  permanece limpo ao final da validação.
- [ ] CA-16: Nenhuma validação em hardware é necessária ou alegada nesta entrega.

## 10. Plano de implementação

1. Criar o workflow com eventos, concorrência, permissões e nomes definidos.
2. Fixar as actions por SHAs verificados e configurar Python, `uv` e cache.
3. Confirmar no README que o comando local é idêntico ao executado na CI.
4. Executar localmente a suíte completa existente.
5. Abrir Pull Request e coletar evidências reais de sucesso e falha no Actions.
6. Após validação, configurar o check como obrigatório na proteção da `main`, se
   o repositório permitir, sem dispensar a revisão humana exigida pelo guia.

## 11. Validação e evidências esperadas

O Pull Request de implementação deverá registrar:

- URL ou identificação das execuções no GitHub Actions;
- commit validado e versão do Python/`uv` exibida no log;
- quantidade total de testes coletados e executados;
- execução local do mesmo comando completo usado na CI;
- evidência controlada de que uma falha de teste falha o check;
- confirmação das permissões e de que nenhum secret foi utilizado;
- confirmação de que nenhum banco de desenvolvimento ou hardware foi acessado.

Não marcar critérios com base apenas na leitura do YAML. Os gatilhos de PR e
push, a concorrência e o nome do check exigem observação no GitHub.

### Evidências locais — 28/09/2026

- Workflow criado em `.github/workflows/backend-tests.yml`, com os três eventos,
  concorrência, permissões e nomes definidos nesta spec.
- SHAs de `actions/checkout` v7.0.1 e `astral-sh/setup-uv` v10.1.0 conferidos nos
  repositórios oficiais antes da inclusão no workflow.
- Formatação do YAML validada com Prettier 3.6.2.
- Ambiente reproduzido localmente com Python 3.12.13 e `uv sync --locked --group dev`.
- `uv run --locked pytest -q`: 44 testes passaram; permaneceram os dois avisos
  de depreciação de dependências já documentados no README do backend.
- `uv run --locked ruff check .` e `uv run --locked ruff format --check .` passaram.
- Nenhuma validação em hardware foi realizada ou é exigida nesta entrega.

Essas evidências não validam os gatilhos, o runner Linux, as permissões efetivas,
a concorrência nem o resultado do check hospedado. Esses itens dependem da
execução do workflow no GitHub Actions.

## 12. Evolução planejada, não aprovada nesta spec

Depois que esta etapa estiver estável, novas specs poderão avaliar:

1. testes unitários isolados quando houver regras que justifiquem essa abordagem;
2. lint e verificação de formatação com Ruff;
3. cobertura e política de limiar;
4. matriz de versões Python suportadas;
5. validações independentes para frontend, otimização e firmware;
6. build e publicação de artefatos;
7. deploy em ambiente de homologação e, depois, produção.

As etapas 6 e 7 dependem da definição do artefato implantável, do provedor de
cloud, dos ambientes, da gestão de credenciais e da estratégia de rollback.
Elas não devem ser implementadas como consequência implícita desta aprovação.

## 13. Decisões aprovadas

| Ponto | Definição |
|---|---|
| Plataforma de automação | GitHub Actions |
| Primeira validação | Suíte automatizada completa do backend, predominantemente de integração |
| Python inicial | 3.12, versão mínima suportada |
| Ambiente | Runner Linux hospedado pelo GitHub |
| Dependências | `uv` com `backend/uv.lock` obrigatório |
| Eventos | PR para `main`, push em `main` e execução manual |
| Seleção | Todos os testes coletados em `backend/tests/` |
| Segurança | Token somente leitura, sem secrets, actions por SHA |
| CD/deploy | Fora do escopo; decisão futura |
| Proteção da `main` | Check estável, configuração após validação real |

A aprovação desta spec não transforma os itens da seção 12 em requisitos.
Mudanças de escopo ou decisões de deploy devem ser registradas e aprovadas em
documentação própria.
