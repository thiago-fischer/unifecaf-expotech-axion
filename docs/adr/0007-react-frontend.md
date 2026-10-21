# ADR-007 — Frontend local em React com TypeScript e Vite

- Status: Aceita pelo responsável na aprovação da SPEC-0006; revisão do PR pendente
- Data: 17/10/2026
- Relacionada: [SPEC-0006](../specs/0006-react-frontend.md) e
  [issue #10](https://github.com/thiago-fischer/unifecaf-expotech-axion/issues/10)

## Contexto

O backend já expõe catálogos, ordens e planejamento em software. A issue #10
exige React para permitir uso local sem depender do Swagger. O responsável
aprovou a SPEC-0006 e autorizou sua implementação nesta data. A arquitetura
anterior ainda mantinha a tecnologia de frontend em aberto.

## Decisão

- Criar `frontend/` no monorepo, separado do FastAPI, com React e TypeScript.
- Usar Vite para desenvolvimento e build, Node.js 24.x e npm com lockfile.
- Usar componentes funcionais e hooks; navegação entre quatro áreas em memória,
  sem roteador, URLs por tela ou biblioteca de estado nesta entrega.
- Centralizar HTTP em `fetch`, preservando status, corpo e `Retry-After`.
- Usar CSS responsivo sem biblioteca de componentes.
- Encaminhar `/api` pelo proxy local do Vite, configurado por `AXION_API_TARGET`,
  sem modificar CORS no backend. O proxy remove o prefixo.
- Testar com Vitest/React Testing Library e Playwright com API real e banco
  descartável; verificar tipos com TypeScript e formatação com Prettier.

## Justificativa e alternativas

React atende ao requisito do responsável. TypeScript explicita os campos
consumidos da API; Vite prepara a SPA sem servidor de aplicação adicional.
Hooks e navegação em memória bastam para o fluxo local de quatro áreas.
Roteador e gerenciador global de estado poderão ser avaliados se surgirem URLs
compartilháveis ou sincronização mais complexa. Uma biblioteca de componentes
não é necessária para formulários e tabela básicos.

O proxy mantém a mesma origem no navegador e evita alterar a API para este
ambiente. Acesso direto com CORS restrito seria viável, mas exigiria configuração
adicional e exposição de `Retry-After`. SSR e frameworks de aplicação completa
não têm necessidade concreta neste escopo local.

## Consequências

- O frontend pode evoluir e ser testado independentemente do backend.
- O planejamento preserva a distinção entre viabilidade e prova de ótimo;
  o resultado continua transitório e sem execução física.
- Trocar de área desmonta a tela: formulários e planos não persistem na navegação.
- O build estático não inclui proxy: outro ambiente precisará encaminhar `/api`.
- O timeout de planejamento de 60 s não constitui garantia de latência do
  servidor nem de cancelamento da busca ao interromper a espera.
- Há uma cadeia de ferramentas Node além do ambiente Python. Dependências
  diretas e transitivas ficam registradas em `frontend/package-lock.json`.

## Reavaliação

Reavaliar navegação, estado e acesso à API quando houver URLs por recurso,
autenticação, deploy, telemetria ou persistência de planos. Essas evoluções não
estão aprovadas por esta ADR. O merge continua exigindo revisão de outro integrante.
