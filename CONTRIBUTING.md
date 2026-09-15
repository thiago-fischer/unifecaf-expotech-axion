# Guia de Contribuição — Axion

Obrigado por contribuir com o **Axion**.

Este documento define as regras básicas para organização, colaboração e envio de alterações no repositório.

O objetivo é manter o projeto organizado, facilitar a revisão entre os integrantes e garantir que as decisões técnicas fiquem registradas durante o desenvolvimento.

## Organização do projeto

O Axion é dividido em módulos relacionados ao sistema de software, automação da maquete, otimização, observabilidade, segurança de rede e documentação.

Estrutura prevista do repositório:

```text
axion/
├── backend/
├── frontend/
├── firmware/
├── optimization/
├── monitoring/
├── docs/
├── .github/
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

Cada contribuição deve ser feita no módulo correspondente. Sempre que uma alteração impactar o funcionamento do projeto, a documentação também deve ser atualizada.

## Tipos de contribuição

As contribuições podem envolver diferentes partes do projeto, como:

- desenvolvimento do frontend;
- desenvolvimento do backend;
- criação ou ajuste do módulo de otimização;
- desenvolvimento do firmware dos dispositivos embarcados;
- integração com sensores, atuadores e displays;
- implementação de observabilidade e métricas;
- análise e mitigação de vulnerabilidades de rede;
- documentação técnica;
- correções, melhorias e refatorações.

## Fluxo de trabalho

Toda alteração relevante deve ser feita em uma branch separada.

Não devem ser feitas alterações diretamente na branch `main`.

Fluxo recomendado:

```text
main
  ↓
criação de branch
  ↓
desenvolvimento
  ↓
commit
  ↓
pull request
  ↓
revisão
  ↓
merge
```

## Nome das branches

Use nomes simples, descritivos e relacionados ao objetivo da alteração.

Exemplos:

```text
feature/cadastro-produtos
feature/criacao-ordem-producao
feature/modulo-otimizacao
feature/comunicacao-esp32
fix/correcao-calculo-tempo-total
docs/arquitetura-inicial
refactor/reorganiza-backend
```

Prefixos recomendados:

- `feature/` para novas funcionalidades;
- `fix/` para correções;
- `docs/` para documentação;
- `refactor/` para reorganização ou melhoria interna de código;
- `test/` para testes;
- `chore/` para ajustes de configuração, estrutura ou manutenção.

## Commits

Os commits devem ser claros e explicar o que foi alterado.

Use mensagens curtas e objetivas.

Exemplos:

```text
feat: adiciona cadastro de produtos
feat: cria endpoint de ordens de produção
fix: corrige cálculo do tempo total da ordem
docs: atualiza documentação da arquitetura
refactor: reorganiza módulo de otimização
test: adiciona testes para criação de ordem
chore: configura workflow inicial do GitHub Actions
```

Evite commits genéricos como:

```text
alterações
teste
ajustes
commit final
corrigido
```

## Pull Requests

Toda alteração relevante deve ser enviada por Pull Request.

O Pull Request deve conter:

- resumo do que foi feito;
- motivo da alteração;
- módulos ou arquivos impactados;
- instruções de teste ou validação;
- indicação se houve alteração na documentação.

Modelo sugerido para descrição do Pull Request:

```md
## Resumo

Descreva brevemente o que foi feito.

## Motivo

Explique por que essa alteração foi necessária.

## Alterações realizadas

- 
- 
- 

## Como testar

Explique como validar a alteração.

## Documentação

Informe se algum documento foi criado ou atualizado.

## Checklist

- [ ] O código foi testado localmente
- [ ] A documentação foi atualizada, se necessário
- [ ] A alteração foi feita em uma branch separada
- [ ] O Pull Request foi revisado por outro integrante
- [ ] Não foram adicionados arquivos desnecessários
```

## Revisão de código

Todo Pull Request deve ser revisado por pelo menos um integrante do grupo antes de ser integrado à branch `main`.

Durante a revisão, devem ser verificados os seguintes pontos:

- se a alteração funciona;
- se o código está compreensível;
- se a solução faz sentido para o projeto;
- se não há arquivos temporários, duplicados ou desnecessários;
- se a documentação foi atualizada quando necessário;
- se a alteração não prejudica outros módulos do sistema.

Comentários de revisão devem ser objetivos, respeitosos e voltados à melhoria do projeto.

## Documentação

Sempre que uma alteração modificar o funcionamento do sistema, a documentação correspondente deve ser atualizada.

Exemplos de documentos previstos:

```text
docs/visao-geral.md
docs/arquitetura.md
docs/requisitos.md
docs/otimizacao.md
docs/maquete.md
docs/rastreabilidade.md
docs/seguranca-rede.md
docs/decisoes.md
```

Mudanças importantes de arquitetura, escopo, tecnologia ou funcionamento devem ser registradas em `docs/decisoes.md` ou em outro documento adequado dentro da pasta `docs/`.

## Testes e validações

Quando o projeto possuir testes automatizados, eles devem ser executados antes da abertura do Pull Request.

Enquanto os testes automatizados ainda não estiverem definidos, o integrante responsável deve informar como validou a alteração manualmente.

Exemplo de validação manual:

```text
Validação realizada:
- aplicação executada localmente;
- cadastro de produto testado;
- criação de ordem de produção testada;
- logs verificados no terminal;
- não foram encontrados erros durante o teste.
```

## CI/CD

O projeto deverá utilizar GitHub Actions para validação automática das alterações.

Quando os workflows estiverem configurados, os Pull Requests deverão passar pelas verificações automáticas antes do merge.

Exemplos de validações que poderão ser incluídas:

- execução de testes automatizados;
- verificação de lint;
- validação de build;
- análise de documentação;
- validação de arquivos de configuração.

## Boas práticas

Ao contribuir com o projeto:

- mantenha o código simples, organizado e legível;
- use nomes claros para arquivos, funções, classes e variáveis;
- evite duplicação desnecessária;
- separe responsabilidades entre os módulos;
- não envie arquivos temporários, caches ou dependências locais;
- atualize a documentação quando a alteração impactar o projeto;
- registre decisões técnicas importantes;
- comunique alterações que afetem outros integrantes.

## Arquivos que não devem ser enviados

Evite enviar arquivos gerados automaticamente ou específicos do ambiente local, como:

```text
node_modules/
.venv/
__pycache__/
.env
.DS_Store
.vscode/
dist/
build/
*.log
```

Caso algum arquivo de configuração local seja necessário, documente um exemplo seguro, como `.env.example`, sem dados sensíveis.

## Segurança

Não devem ser enviados ao repositório:

- senhas;
- tokens;
- chaves de API;
- credenciais de banco de dados;
- arquivos `.env` com informações reais;
- dados sensíveis de rede ou infraestrutura.

Quando necessário, use variáveis de ambiente e arquivos de exemplo sem informações privadas.

## Licença

Ao contribuir com este projeto, você concorda que suas contribuições serão disponibilizadas sob a licença MIT.

Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
