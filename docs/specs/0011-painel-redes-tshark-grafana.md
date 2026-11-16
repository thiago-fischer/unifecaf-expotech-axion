# SPEC-0011 — Painel de redes com TShark e Grafana

> **Status:** Implementada e validada localmente em 14/11/2026; aguarda revisão
> de outro integrante e execução da CI no Pull Request.
>
> **Data:** 14/11/2026
>
> **Origem:** Requisito de Telecomunicações para visualizar a comunicação da
> plataforma antes da disponibilidade da maquete física.

## 1. Objetivo

Adicionar ao frontend do Axion uma área **Rede** capaz de apresentar:

- topologia dos componentes da plataforma;
- estado de comunicação entre backend, controlador, PostgreSQL e Grafana;
- metadados sanitizados do tráfego recente capturado com TShark;
- indicadores básicos de segurança do laboratório;
- métricas históricas agregadas em um novo dashboard provisionado no Grafana.

O painel deve usar dados reais do ambiente local e distinguir claramente:

- estado da aplicação, obtido das APIs existentes;
- tráfego observado pelo TShark;
- métricas históricas persistidas;
- conexões apenas configuradas, mas não observadas pela captura atual.

Esta entrega é uma ferramenta de laboratório e apresentação. Ela não substitui
um IDS, um SIEM, monitoramento de produção ou validação da comunicação com
hardware real.

## 2. Dependências e estado atual

Esta proposta depende das entregas existentes:

- [SPEC-0006](0006-react-frontend.md): frontend React com navegação local;
- [SPEC-0008](0008-migracao-postgresql.md): PostgreSQL em rede e migrations;
- [SPEC-0009](0009-api-controlador-maquete.md): controlador simulado e eventos
  HTTP;
- [SPEC-0010](0010-grafana-postgresql.md): Grafana 13.3.1, datasource
  PostgreSQL somente leitura e provisioning versionado;
- [ADR-009](../adr/0009-postgresql-banco-em-rede.md): backend como único
  escritor dos dados de domínio e Grafana como consumidor de leitura.

O frontend já consulta `GET /simulation/status`, com maior frequência durante
uma execução. Essa resposta contém sessão, sequência, idade do snapshot,
comandos ativos, máquinas, peças, RFID, QA, falhas e estado da OP. Esses campos
podem alimentar a visão operacional sem captura de pacotes.

O Grafana já está disponível em container, mas atualmente apresenta somente
cadastros e ordens persistidos. Não existem tabela de métricas de rede,
dashboard de rede nem serviço TShark.

O uso de HTTP no controlador simulado não define o protocolo futuro da maquete
física. O protocolo entre dispositivos permanece uma decisão em aberto; esta
spec cobre apenas o laboratório de software atual.

## 3. Decisões propostas

1. Utilizar TShark em um container auxiliar e opcional, sem interface gráfica.
2. Compartilhar o namespace de rede do backend para observar somente o tráfego
   que entra ou sai desse serviço.
3. Executar a captura apenas pelo profile Compose `network-lab`.
4. Não armazenar pacotes brutos, payloads, cabeçalhos ou arquivos PCAP.
5. Enviar ao backend somente campos previamente permitidos e sanitizados.
6. Manter os eventos recentes em buffer circular na memória do backend.
7. Persistir somente agregados temporais necessários ao dashboard histórico.
8. Fazer o frontend consultar o backend; o navegador não acessará TShark,
   PostgreSQL ou APIs administrativas do Grafana diretamente.
9. Exibir o Grafana por status e link externo, sem `iframe`.
10. Não permitir iniciar, parar ou reconfigurar a captura pelo frontend.

Essas decisões tornam-se obrigatórias somente após a aceitação desta spec. Uma
mudança relevante no modelo de captura ou armazenamento deverá ser registrada
em ADR antes da implementação.

## 4. Escopo

### 4.1 Incluído

- Nova área `Rede` na navegação principal do frontend.
- Topologia visual da plataforma com conexões monitoradas e não monitoradas.
- Estado do backend, controlador, PostgreSQL, captura e Grafana.
- Container de captura com TShark e coletor mínimo.
- Profile Compose `network-lab` desabilitado por padrão.
- API interna autenticada para receber lotes de metadados capturados.
- API pública do backend para resumo, eventos recentes e configuração segura da
  visualização.
- Buffer em memória com os eventos recentes.
- Agregação e persistência de métricas de rede por intervalo.
- Migrations Alembic para as tabelas novas.
- Retenção automática e limitada dos agregados.
- Dashboard Grafana **Axion — Rede e comunicação** provisionado por arquivo.
- Link do frontend para abrir o dashboard no Grafana.
- Estados de carregamento, captura desativada, perda de comunicação, vazio e
  falha parcial.
- Testes de parser, segurança, API, persistência, frontend, provisioning e
  integração local.
- Documentação de execução e validação exclusivamente em software/rede local.

### 4.2 Fora do escopo

- Interface gráfica do Wireshark dentro de container.
- Armazenamento ou download de PCAP/PCAPNG.
- Exibição de payloads, corpos HTTP, SQL, headers ou credenciais.
- Captura do tráfego Wi-Fi pelo ar.
- Modo monitor em adaptador sem fio.
- Captura direta de Arduino, ESP32 ou maquete física.
- Inspeção TLS mediante chaves de sessão.
- IDS, IPS, SIEM, detecção automática de intrusão ou classificação por IA.
- Controle remoto do TShark pelo navegador.
- Botão para gerar ataque, falsificar evento ou desabilitar autenticação.
- Prometheus, Loki, Tempo ou OpenTelemetry.
- Alertas e notificações do Grafana.
- Exposição do painel, Grafana ou banco à rede local.
- Definição do protocolo definitivo dos dispositivos físicos.
- Definição final da vulnerabilidade da disciplina de Telecomunicações.

## 5. Arquitetura proposta

```text
Frontend/Nginx
     |
     | HTTP /api
     v
Backend FastAPI <----------> Controlador simulado
     |     ^                      HTTP :8001
     |     |
     |     +-- namespace observado pelo TShark
     |
     +----------------------> PostgreSQL :5432
     |                             ^
     |                             |
     |                        Grafana 13.3.1
     |                             |
     |                             +-- dashboard histórico
     |
     +-- buffer recente em memória
     +-- agregados de rede no PostgreSQL
```

O serviço de captura utilizará:

```yaml
profiles: [network-lab]
network_mode: "service:backend"
cap_drop: [ALL]
cap_add: [NET_ADMIN, NET_RAW]
```

Também deverá utilizar usuário não root após a preparação da imagem, filesystem
somente leitura quando possível, `no-new-privileges`, `tmpfs` para temporários,
nenhuma porta publicada e nenhum acesso ao socket Docker.

Não será usado `privileged: true`.

### 5.1 Limite de visibilidade

Compartilhar a rede do backend permite observar:

- frontend/Nginx → backend;
- backend → controlador;
- controlador → backend;
- backend → PostgreSQL.

Essa captura não observa automaticamente:

- Grafana → PostgreSQL;
- tráfego interno que não passa pelo backend;
- tráfego do host fora do namespace compartilhado;
- comunicação sem fio da futura maquete.

A topologia deverá diferenciar visualmente conexão **observada**, conexão
**configurada** e componente **sem comunicação**. O frontend não poderá afirmar
que um enlace foi capturado quando seu namespace não estiver visível.

## 6. Captura e sanitização

### 6.1 Ferramenta

A imagem do serviço deverá fixar uma versão testada do Wireshark/TShark. Não
será usada tag `latest`. A versão e o digest escolhidos deverão ser registrados
na implementação e atualizados apenas por alteração revisada.

O processo de captura usará filtro BPF restrito ao laboratório, equivalente a:

```text
tcp and (port 8000 or port 8001 or port 5432)
```

O TShark deverá resolver apenas campos necessários, sem resolução DNS externa e
sem hexdump. A saída será processada em streaming; não haverá arquivo de captura
persistente.

### 6.2 Campos permitidos

Cada evento sanitizado poderá conter:

- sessão e sequência da captura;
- horário observado;
- serviço de origem e destino;
- porta de origem e destino;
- protocolo classificado;
- número do fluxo TCP;
- tamanho do frame;
- método HTTP;
- caminho HTTP sem query string;
- classe ou código de resposta HTTP;
- duração calculada entre requisição e resposta;
- indicador de retransmissão ou reset TCP.

### 6.3 Campos proibidos

O coletor não enviará nem registrará:

- payload bruto;
- corpo JSON;
- SQL executado;
- cookies;
- `Authorization`;
- `X-Axion-Event-Token`;
- `X-Axion-Capture-Token`;
- senhas, tokens ou URLs com credenciais;
- RFID completo obtido de payload;
- parâmetros de query;
- dump hexadecimal.

Rotas com identificadores poderão ser normalizadas, por exemplo
`/orders/123/executions` para `/orders/{id}/executions`, evitando cardinalidade
desnecessária no histórico.

## 7. Coletor e entrega ao backend

O coletor executará junto do TShark no serviço de captura. Ele converterá a
saída permitida em lotes pequenos e enviará ao backend pelo endereço de loopback
compartilhado no namespace.

### 7.1 Lote interno

Cada lote deverá conter:

```text
batch_id                 UUID único
capture_session_id       identificador da execução do coletor
first_sequence           primeira sequência do lote
last_sequence            última sequência do lote
captured_at              horário do lote
events                   até 100 eventos sanitizados
```

O coletor repetirá um lote não confirmado usando o mesmo `batch_id`. O backend
deverá tratar a repetição de forma idempotente para não duplicar métricas.

### 7.2 Autenticação

O endpoint interno exigirá `X-Axion-Capture-Token`. O token será obrigatório ao
ativar o profile `network-lab`, será configurado por ambiente nos dois serviços
e comparado de forma resistente a timing.

O frontend/Nginx deverá responder `404` para o caminho interno, seguindo a
proteção já usada em `/api/controller/events`.

Lotes ausentes, inválidos ou sem autenticação não atualizarão buffer nem
métricas.

## 8. Persistência

### 8.1 Lotes processados

Criar `network_capture_batches` com, no mínimo:

- `id`: UUID ou string, chave primária;
- `capture_session_id`;
- `first_sequence`;
- `last_sequence`;
- `received_at` com timezone.

A tabela servirá somente para idempotência. Não armazenará eventos individuais.

### 8.2 Métricas agregadas

Criar `network_metric_samples` com, no mínimo:

- `id`: chave primária;
- `bucket_start`: início do intervalo com timezone e índice;
- `source_service`;
- `destination_service`;
- `protocol`;
- `status_class`, opcional;
- `request_count`;
- `error_count`;
- `bytes_total`;
- `retransmission_count`;
- `latency_sum_ms`;
- `latency_count`.

Os campos numéricos terão constraints para valores não negativos. A combinação
de intervalo, origem, destino, protocolo e classe de status deverá impedir
duplicação lógica.

A latência média histórica será calculada por:

```text
SUM(latency_sum_ms) / NULLIF(SUM(latency_count), 0)
```

Não será persistida uma média de médias.

### 8.3 Transação e camadas

O backend processará cada lote em uma única transação:

1. verificar `batch_id`;
2. registrar o lote quando novo;
3. agregar os eventos nos intervalos;
4. persistir ou atualizar os agregados;
5. confirmar a transação;
6. publicar os eventos sanitizados no buffer em memória.

Controllers tratarão HTTP, services aplicarão deduplicação, agregação e
retenção, repositories executarão consultas, models representarão as tabelas e
schemas Pydantic definirão os contratos. O controller não acessará o banco
diretamente.

As tabelas serão criadas por migration Alembic versionada. `create_all()` não
será usado.

### 8.4 Retenção

Valores propostos:

- buffer ao vivo: últimos 200 eventos em memória;
- lotes processados: 24 horas;
- métricas agregadas: 7 dias;
- intervalo de agregação: 10 segundos.

A retenção será configurável dentro de limites documentados. A limpeza deverá
ser incremental e não bloquear a ingestão. Não haverá retenção ilimitada.

## 9. API do backend

### 9.1 Endpoint interno

| Método e rota | Uso |
|---|---|
| `POST /network/capture/events` | Recebe lote autenticado e idempotente do coletor. Retorna `204`. |

Respostas previstas:

- `204`: lote novo ou repetição já processada;
- `403`: token ausente ou incorreto;
- `422`: schema, sequência ou tamanho inválido;
- `503`: persistência indisponível, permitindo reenvio do mesmo lote.

### 9.2 Endpoints consumidos pelo frontend

| Método e rota | Uso |
|---|---|
| `GET /network/overview` | Topologia, saúde, segurança e resumo da captura. |
| `GET /network/events?after={sequence}&limit={limit}` | Eventos recentes após uma sequência. |

`limit` aceitará de 1 a 100. A resposta de eventos conterá a próxima sequência,
indicador de perda por rotação do buffer e a idade do último lote.

### 9.3 Estado dos serviços

O backend não receberá acesso ao socket Docker. O resumo será calculado por
verificações de aplicação:

- backend: serviço respondendo à própria requisição;
- PostgreSQL: consulta mínima pela sessão existente;
- controlador: snapshot ou consulta pelo `ControllerClient` existente;
- captura: idade do último lote ou heartbeat autenticado;
- Grafana: `GET /api/health` pela rede Docker.

Estados permitidos:

- `online`;
- `degraded`;
- `offline`;
- `disabled`;
- `unknown`.

Falha no Grafana ou na captura não derrubará rotas de produção, planejamento ou
simulação.

### 9.4 Informações de segurança

O resumo poderá informar apenas booleanos e estados, como:

- token do controlador configurado;
- token da captura configurado;
- comunicação local sem TLS;
- portas restritas ao host na configuração conhecida;
- armazenamento de captura bruta desabilitado.

Valores de tokens e senhas nunca serão retornados.

## 10. Frontend

### 10.1 Navegação

Adicionar `Rede` ao tipo `Area`, ao menu principal e ao roteamento local. A nova
página será carregada sob demanda para não aumentar desnecessariamente o bundle
inicial.

### 10.2 Estrutura da página

A página terá três visões locais:

1. **Visão geral**
   - topologia dos serviços;
   - legenda de conexões observadas e configuradas;
   - estado de backend, controlador, PostgreSQL, captura e Grafana;
   - horário do último evento.
2. **Captura ao vivo**
   - fluxo recente de eventos sanitizados;
   - filtros locais por protocolo e conexão;
   - método, rota normalizada, status, bytes, latência e indicação TCP;
   - detalhes da execução obtidos de `/simulation/status`, quando houver OP.
3. **Segurança**
   - indicadores de autenticação e exposição local;
   - eventos aceitos ou bloqueados já observados;
   - link para documentação do laboratório;
   - aviso explícito de que HTTP local não oferece confidencialidade.

A troca entre as visões não fará requisições destrutivas nem controlará o
serviço de captura.

### 10.3 Atualização

Enquanto a visão ao vivo estiver aberta:

- consultar novos eventos a cada 500 ms durante tráfego ativo;
- reduzir para 2 s quando não houver eventos;
- interromper timers ao sair da página;
- usar `after` para não baixar novamente todo o buffer;
- limitar a lista renderizada a 200 itens.

WebSocket e SSE ficam fora do MVP. O polling será reavaliado apenas com medição
de necessidade.

### 10.4 Estados e acessibilidade

O frontend deverá representar:

- conectando;
- captura desabilitada;
- captura ativa sem tráfego;
- fluxo ativo;
- histórico parcialmente perdido por rotação;
- backend indisponível;
- controlador indisponível;
- Grafana indisponível;
- erro parcial sem remover os últimos dados válidos.

Status não dependerá somente de cor. Tabelas, filtros e abas deverão funcionar
por teclado. Atualizações frequentes não serão anunciadas individualmente por
leitores de tela; apenas mudanças relevantes de estado usarão `aria-live`.

### 10.5 Integração com Grafana

O backend fornecerá:

- estado do Grafana;
- URL pública configurada;
- UID do dashboard de rede.

O frontend exibirá **Abrir dashboard no Grafana** em nova aba. Não será usado
`iframe`, não serão encaminhadas credenciais e o link não será mostrado como
saudável se `/api/health` falhar.

## 11. Dashboard Grafana

Provisionar **Axion — Rede e comunicação**, UID estável
`axion-rede-comunicacao`, na pasta `Axion`.

### 11.1 Painéis obrigatórios

1. Requisições por minuto.
2. Erros por classe de status.
3. Bytes observados por conexão.
4. Latência média ponderada por conexão.
5. Retransmissões TCP por intervalo.
6. Distribuição por protocolo.
7. Disponibilidade de amostras por origem e destino.
8. Tabela dos agregados recentes.

Consultas usarão `bucket_start` e macros temporais do Grafana. O dashboard não
consultará o buffer em memória nem dependerá do backend para renderizar o
histórico.

O datasource `Axion PostgreSQL` existente será reutilizado. A role
`grafana_reader` receberá `SELECT` explícito nas novas tabelas após a migration.
O Grafana não gravará métricas.

Quando não houver amostras, os painéis mostrarão estado vazio compreensível e
não inventarão valores zero para intervalos não observados.

## 12. Configuração prevista

Variáveis propostas:

```text
AXION_CAPTURE_TOKEN=
AXION_NETWORK_CAPTURE_ENABLED=false
AXION_NETWORK_EVENT_BUFFER_SIZE=200
AXION_NETWORK_BUCKET_SECONDS=10
AXION_NETWORK_METRICS_RETENTION_HOURS=168
AXION_NETWORK_BATCH_RETENTION_HOURS=24
AXION_GRAFANA_URL=http://grafana:3000
AXION_GRAFANA_PUBLIC_URL=http://127.0.0.1:3000
AXION_GRAFANA_NETWORK_DASHBOARD_UID=axion-rede-comunicacao
```

O profile `network-lab` deverá falhar claramente se a captura for ativada sem
token. Exemplos usarão valores locais não sensíveis; credenciais reais e `.env`
permanecerão fora do Git.

## 13. Segurança e riscos

### 13.1 Capacidades de rede

`NET_ADMIN` e `NET_RAW` aumentam o impacto potencial do container de captura.
Controles obrigatórios:

- profile opcional;
- nenhuma execução em ambientes não autorizados;
- sem `privileged`;
- imagem e dependências fixadas;
- processo não root;
- sem socket Docker;
- sem portas publicadas;
- filesystem somente leitura quando compatível;
- código do coletor pequeno e revisável.

### 13.2 Dados sensíveis

O parser seguirá allowlist de campos. Não será suficiente remover campos depois
de armazenar JSON completo do TShark. A saída bruta não deverá sair do processo
de sanitização nem ser escrita em volume.

Logs não conterão eventos completos, senhas, tokens ou payloads. Diagnósticos
usarão contagens, sequências e códigos de erro.

### 13.3 Cardinalidade e volume

Rotas serão normalizadas, serviços terão conjunto conhecido e campos livres
terão limites. Lotes, buffer, frequência e retenção terão tetos. Eventos fora da
allowlist serão descartados.

### 13.4 Interpretação

Ausência de pacote não comprova ausência de comunicação fora do namespace
observado. HTTP decodificado não significa comunicação protegida. A interface
deverá mostrar o alcance da captura para evitar conclusões incorretas no pitch.

## 14. Falhas e recuperação

- TShark parado: painel mostra captura offline; aplicação continua funcionando.
- Profile desabilitado: painel mostra captura desabilitada, sem erro global.
- Backend reiniciado: buffer ao vivo é perdido; métricas persistidas permanecem.
- Grafana parado: link fica indisponível; painel ao vivo continua.
- PostgreSQL parado: ingestão retorna `503`; coletor repete o lote com mesmo ID.
- Lote duplicado: backend retorna sucesso sem duplicar agregados.
- Lote maior que o limite: backend rejeita com `422`.
- Evento antigo ou sequência inválida: lote rejeitado e diagnóstico sem payload.
- Retenção atrasada: limpeza é retomada em lote sem apagar dados recentes.

## 15. Testes e validação

### 15.1 Backend

- autenticação obrigatória do endpoint interno;
- comparação segura do token;
- schema e limite de 100 eventos;
- idempotência por `batch_id`;
- agregação por intervalo, fluxo, protocolo e status;
- média ponderada por soma e contagem;
- constraints e migration upgrade/downgrade;
- retenção de lotes e métricas;
- buffer circular e sinalização de rotação;
- falhas independentes de controlador, banco, captura e Grafana;
- ausência de token e payload nas respostas e logs controlados.

### 15.2 Coletor

- fixtures TShark para HTTP, TCP, retransmissão e PostgreSQL;
- allowlist de campos;
- remoção de query string;
- normalização de rotas;
- correlação de requisição e resposta;
- lote máximo e sequência crescente;
- repetição com mesmo `batch_id` após falha;
- execução sem escrita de PCAP;
- falha sem token obrigatório.

### 15.3 Frontend

- navegação e carregamento sob demanda;
- topologia e legenda de alcance;
- estados ativo, vazio, desabilitado, degradado e offline;
- polling adaptativo e cancelamento ao desmontar;
- filtros locais;
- rotação do buffer;
- link seguro para o Grafana;
- acessibilidade por teclado e leitores de tela;
- ausência de controles de captura ou ataque.

### 15.4 Grafana

- datasource existente reutilizado;
- dashboard provisionado com UID estável;
- todas as consultas somente leitura;
- painéis com banco vazio e com amostras;
- macros temporais aplicadas a `bucket_start`;
- role do Grafana sem permissão de escrita nas tabelas novas.

### 15.5 Integração local

1. Subir o ambiente normal sem profile e confirmar painel degradado, mas útil.
2. Subir com `--profile network-lab` e token definido.
3. Criar e executar uma OP simulada.
4. Confirmar fluxo frontend → backend → controlador e backend → PostgreSQL.
5. Confirmar que nenhum payload ou token aparece na API, frontend, banco ou
   logs.
6. Confirmar agregados no Grafana após o primeiro intervalo.
7. Parar captura, controlador e Grafana separadamente e validar degradação.
8. Reenviar lote e provar ausência de duplicação.

Essa validação é de software e rede Docker. Não será descrita como teste de
hardware, Wi-Fi ou maquete física.

## 16. Critérios de aceite

- [x] Decisões de captura, retenção e capacidades aprovadas na ADR-012.
- [x] Serviço TShark usa versão fixa e profile `network-lab`.
- [x] Container não usa `privileged`, socket Docker nem porta publicada.
- [x] Nenhum PCAP, payload, header sensível ou SQL é persistido.
- [x] Endpoint interno exige token e fica bloqueado pelo Nginx.
- [x] Lotes repetidos não duplicam métricas.
- [x] Migrations criam e removem as tabelas de rede de forma reproduzível.
- [x] Backend preserva arquitetura em camadas.
- [x] Buffer ao vivo respeita limite e informa rotação.
- [x] Retenção remove somente dados expirados.
- [x] `/network/overview` representa saúde sem usar o socket Docker.
- [x] `/network/events` pagina por sessão e sequência e limita resultados.
- [x] Frontend possui área `Rede` responsiva e acessível.
- [x] Conexões observadas e apenas configuradas são diferenciadas.
- [x] Frontend não controla a captura nem executa ataques.
- [x] Link para Grafana funciona sem encaminhar credenciais.
- [x] Dashboard `Axion — Rede e comunicação` é provisionado.
- [x] Consultas do Grafana são somente leitura e usam dados reais.
- [x] Role do Grafana não consegue alterar as tabelas de rede.
- [x] Falha da captura ou do Grafana não interrompe o Axion.
- [x] Testes automatizados e integração local são aprovados.
- [x] Documentação informa limites da captura e ausência de hardware real.

## 17. Sequência de implementação proposta

1. Aprovar esta spec e registrar ADR se exigido pela revisão.
2. Criar models, migration, repositories e services de métricas.
3. Implementar contratos e endpoints do backend.
4. Implementar coletor com fixtures controladas antes de conceder capacidades.
5. Integrar o serviço ao profile `network-lab`.
6. Implementar a página `Rede` com dados simulados apenas nos testes.
7. Provisionar o dashboard Grafana de rede.
8. Executar validação de segurança, volume, falhas e integração ponta a ponta.
9. Atualizar status da spec somente com evidências registradas.

## 18. Decisões resolvidas e limites mantidos

- Debian 12.12 slim por digest e TShark `4.0.17-0+deb12u3` foram fixados.
- A [ADR-012](../adr/0012-captura-sanitizada-de-rede.md) registra capacidades,
  sanitização, retenção, cursor e mitigação da realimentação da captura.
- A retenção inicial permanece em 24 horas para lotes e 7 dias para agregados,
  com buckets de 10 segundos e buffer de 200 eventos.
- Segmentos numéricos e UUID são normalizados; query strings são descartadas.
- Os oito painéis da seção 11 definem as métricas entregues nesta versão.
- Captura adicional no namespace do PostgreSQL foi excluída do MVP.
- A vulnerabilidade do pitch e o protocolo da maquete física permanecem fora do
  escopo desta implementação e exigem decisão própria quando forem definidos.

## 19. Referências

- [Visão geral — Telecomunicações e Segurança de Rede](../visao-geral.md#11-telecomunicações-e-segurança-de-rede)
- [ADR-009 — PostgreSQL como banco de dados em rede](../adr/0009-postgresql-banco-em-rede.md)
- [SPEC-0009 — API do controlador e execução simulada](0009-api-controlador-maquete.md)
- [SPEC-0010 — Grafana com PostgreSQL](0010-grafana-postgresql.md)
- [Wireshark — Capture privileges](https://wiki.wireshark.org/capturesetup/captureprivileges)
- [TShark manual](https://www.wireshark.org/docs/man-pages/tshark)
- [Dumpcap manual](https://www.wireshark.org/docs/man-pages/dumpcap.html)
- [Docker Compose — `network_mode`](https://docs.docker.com/reference/compose-file/services/#network_mode)
- [Grafana — PostgreSQL data source](https://grafana.com/docs/grafana/latest/datasources/postgres/)
- [Grafana — Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)
