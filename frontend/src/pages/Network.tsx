import { useEffect, useMemo, useRef, useState } from 'react';
import { request } from '../api/client';
import type { NetworkEvent, NetworkEventsResponse, NetworkOverview } from '../api/types';

type View = 'overview' | 'live' | 'security';

function Status({ value }: { value: string }) {
  return <span className={`network-status ${value}`}>{value}</span>;
}

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleTimeString('pt-BR') : 'nenhum evento';
}

export default function Network() {
  const [view, setView] = useState<View>('overview');
  const [overview, setOverview] = useState<NetworkOverview>();
  const [events, setEvents] = useState<NetworkEvent[]>([]);
  const [error, setError] = useState('');
  const [historyLost, setHistoryLost] = useState(false);
  const [protocol, setProtocol] = useState('all');
  const [connection, setConnection] = useState('all');
  const cursor = useRef({ session: null as string | null, sequence: 0 });

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const data = await request<NetworkOverview>('/network/overview');
        if (active) {
          setOverview(data);
          setError('');
        }
      } catch (caught) {
        if (active) setError((caught as Error).message);
      }
    }
    void load();
    const timer = setInterval(() => void load(), 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (view !== 'live') return;
    let active = true;
    let timer = 0;
    async function poll() {
      let delay = 2000;
      try {
        const current = cursor.current;
        const session = current.session
          ? `&capture_session_id=${encodeURIComponent(current.session)}`
          : '';
        const data = await request<NetworkEventsResponse>(
          `/network/events?after=${current.sequence}&limit=100${session}`,
        );
        if (!active) return;
        if (data.session_changed) setEvents([]);
        if (data.events.length) {
          setEvents((previous) => [...previous, ...data.events].slice(-200));
          delay = 500;
        }
        cursor.current = {
          session: data.capture_session_id,
          sequence: data.next_sequence,
        };
        setHistoryLost(data.history_lost);
        setError('');
      } catch (caught) {
        if (active) setError((caught as Error).message);
      } finally {
        if (active) timer = window.setTimeout(() => void poll(), delay);
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [view]);

  const connections = useMemo(
    () => [
      ...new Set(events.map((event) => `${event.source_service} → ${event.destination_service}`)),
    ],
    [events],
  );
  const filtered = events.filter(
    (event) =>
      (protocol === 'all' || event.protocol === protocol) &&
      (connection === 'all' ||
        `${event.source_service} → ${event.destination_service}` === connection),
  );
  const grafanaOnline = overview?.services.grafana?.state === 'online';
  const grafanaLink = overview
    ? `${overview.grafana_public_url.replace(/\/$/, '')}/d/${encodeURIComponent(overview.grafana_dashboard_uid)}`
    : '';

  return (
    <div className="network-page">
      <div className="network-tabs" role="tablist" aria-label="Visões da rede">
        {(
          [
            ['overview', 'Visão geral'],
            ['live', 'Captura ao vivo'],
            ['security', 'Segurança'],
          ] as const
        ).map(([id, label]) => (
          <button
            className="secondary"
            role="tab"
            aria-selected={view === id}
            key={id}
            onClick={() => setView(id)}
          >
            {label}
          </button>
        ))}
      </div>
      {error && (
        <p className="notice error" role="alert">
          {error} Os últimos dados válidos continuam visíveis.
        </p>
      )}

      {view === 'overview' && (
        <>
          <section className="panel" aria-labelledby="services-title">
            <div className="panel-heading">
              <h2 id="services-title">Componentes</h2>
              <small>Último evento: {formatTime(overview?.last_event_at ?? null)}</small>
            </div>
            {!overview ? (
              <p role="status">Consultando estado dos serviços…</p>
            ) : (
              <div className="service-grid">
                {Object.entries(overview.services).map(([name, health]) => (
                  <article key={name} className="service-card">
                    <strong>{name}</strong>
                    <Status value={health.state} />
                    {health.detail && <small>{health.detail}</small>}
                  </article>
                ))}
              </div>
            )}
          </section>
          <section className="panel" aria-labelledby="topology-title">
            <h2 id="topology-title">Topologia observável</h2>
            <p>
              <span className="legend observed">Observada</span> confirma tráfego capturado.{' '}
              <span className="legend configured">Configurada</span> representa uma conexão
              conhecida, ainda sem pacote no namespace do backend.
            </p>
            <ul className="connection-list">
              {overview?.connections.map((item) => (
                <li key={`${item.source}-${item.destination}`}>
                  <strong>{item.source}</strong> → <strong>{item.destination}</strong>{' '}
                  <span className={`legend ${item.visibility}`}>{item.visibility}</span>
                </li>
              ))}
            </ul>
            {grafanaOnline ? (
              <a className="button-link" href={grafanaLink} target="_blank" rel="noreferrer">
                Abrir dashboard no Grafana
              </a>
            ) : (
              <p className="hint">
                O link do dashboard ficará disponível quando o Grafana responder.
              </p>
            )}
          </section>
        </>
      )}

      {view === 'live' && (
        <section className="panel" aria-labelledby="capture-title">
          <div className="panel-heading">
            <h2 id="capture-title">Metadados sanitizados</h2>
            <span aria-live="polite">
              {overview?.services.capture?.state === 'disabled'
                ? 'Captura desativada'
                : `${events.length} eventos recentes`}
            </span>
          </div>
          {historyLost && (
            <p className="notice">Parte do histórico saiu do buffer circular antes da leitura.</p>
          )}
          <div className="network-filters">
            <label>
              Protocolo
              <select value={protocol} onChange={(event) => setProtocol(event.target.value)}>
                <option value="all">Todos</option>
                <option>HTTP</option>
                <option>PostgreSQL</option>
                <option>TCP</option>
              </select>
            </label>
            <label>
              Conexão
              <select value={connection} onChange={(event) => setConnection(event.target.value)}>
                <option value="all">Todas</option>
                {connections.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="table-scroll">
            <table>
              <caption>
                Fluxo observado; corpos, cabeçalhos, SQL e query strings não são coletados.
              </caption>
              <thead>
                <tr>
                  <th>Horário</th>
                  <th>Conexão</th>
                  <th>Protocolo</th>
                  <th>Operação</th>
                  <th>Status</th>
                  <th>Bytes</th>
                  <th>Latência</th>
                  <th>TCP</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((event) => (
                  <tr key={`${event.capture_session_id}-${event.sequence}`}>
                    <td>{formatTime(event.observed_at)}</td>
                    <td>
                      {event.source_service} → {event.destination_service}
                    </td>
                    <td>{event.protocol}</td>
                    <td>{[event.http_method, event.http_path].filter(Boolean).join(' ') || '—'}</td>
                    <td>{event.status_code ?? '—'}</td>
                    <td>{event.frame_length}</td>
                    <td>{event.latency_ms === null ? '—' : `${event.latency_ms.toFixed(1)} ms`}</td>
                    <td>
                      {event.reset ? 'reset' : event.retransmission ? 'retransmissão' : 'normal'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!filtered.length && (
            <p className="empty">Nenhum evento corresponde aos filtros atuais.</p>
          )}
        </section>
      )}

      {view === 'security' && (
        <section className="panel security-panel" aria-labelledby="security-title">
          <h2 id="security-title">Controles do laboratório</h2>
          <ul>
            <li>
              Token do controlador:{' '}
              {overview?.security.controller_token_configured ? 'configurado' : 'ausente'}
            </li>
            <li>
              Token da captura:{' '}
              {overview?.security.capture_token_configured ? 'configurado' : 'ausente'}
            </li>
            <li>Portas dos serviços: restritas ao host na configuração Compose</li>
            <li>Captura bruta e arquivos PCAP: desabilitados</li>
            <li>Lotes aceitos nesta execução: {overview?.security.accepted_batches ?? 0}</li>
            <li>Lotes bloqueados nesta execução: {overview?.security.blocked_batches ?? 0}</li>
          </ul>
          <p className="notice">
            O laboratório usa HTTP local. Os metadados exibidos não significam que a comunicação
            possui confidencialidade, e a ausência de eventos não prova ausência de tráfego fora do
            namespace observado.
          </p>
          <a href="/network-lab.md" target="_blank" rel="noreferrer">
            Abrir documentação do laboratório
          </a>
        </section>
      )}
    </div>
  );
}
