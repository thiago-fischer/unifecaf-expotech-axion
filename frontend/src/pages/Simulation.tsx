import { useEffect, useRef, useState } from 'react';
import Scene from '../simulation/Scene';
import { advance, colors, createState, locationLabel, nextEvent } from '../simulation/engine';
import '../simulation/simulation.css';
export default function Simulation() {
  const state = useRef(createState());
  const [, refresh] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [selected, setSelected] = useState('MAT-001');
  const [camera, setCamera] = useState(0);
  const [reduced, setReduced] = useState(
    () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false,
  );
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const change = () => setReduced(query.matches);
    query.addEventListener('change', change);
    return () => query.removeEventListener('change', change);
  }, []);
  useEffect(() => {
    const hide = () => {
      if (document.hidden) setRunning(false);
    };
    document.addEventListener('visibilitychange', hide);
    return () => document.removeEventListener('visibilitychange', hide);
  }, []);
  useEffect(() => {
    if (!running) return;
    let frame = 0,
      last = performance.now(),
      paint = last;
    const tick = (now: number) => {
      advance(state.current, ((now - last) / 1000) * speed);
      last = now;
      if (now - paint > 80) {
        refresh((n) => n + 1);
        paint = now;
      }
      if (state.current.status === 'complete' || state.current.status === 'blocked') {
        setRunning(false);
        refresh((n) => n + 1);
      } else frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [running, speed]);
  const s = state.current;
  const unit = s.units.find((u) => u.id === selected)!;
  const finished = s.status === 'complete' || s.status === 'blocked';
  const status =
    s.status === 'complete'
      ? 'Ciclo concluído'
      : s.status === 'blocked'
        ? 'Simulação bloqueada'
        : running
          ? 'Em execução'
          : s.status === 'ready'
            ? 'Pronta para iniciar'
            : 'Pausada';
  return (
    <section className="simulation" aria-label="Simulação da maquete">
      <div className="sim-top">
        <div>
          <span className="sim-tag">DEMONSTRAÇÃO SIMULADA</span>
          <h2>
            Uma fábrica em movimento<span>.</span>
          </h2>
          <p>Seis unidades. Três estações. Cada movimento tem uma história.</p>
        </div>
        <span className="sim-status" role="status">
          {status}
        </span>
      </div>
      <div className="sim-stage">
        <div className="sim-overlay">
          <span>
            AXION LAB <b>/ 01</b>
          </span>
          <small>MAQUETE VIRTUAL · CAPTURA CONCEITUAL</small>
        </div>
        <Scene state={state} select={setSelected} reset={camera} reduced={reduced} />
        <div className="sim-stage-bottom">
          <span>Arraste para orbitar · Role para aproximar</span>
          <button onClick={() => setCamera((n) => n + 1)}>Restaurar câmera</button>
        </div>
      </div>
      <div className="sim-controls">
        <button disabled={finished} onClick={() => setRunning(!running)}>
          {running ? 'Pausar' : s.status === 'ready' ? 'Iniciar' : 'Continuar'}
        </button>
        <button
          disabled={running || finished}
          onClick={() => {
            nextEvent(s);
            refresh((n) => n + 1);
          }}
        >
          Próximo evento
        </button>
        <button
          onClick={() => {
            setRunning(false);
            state.current = createState();
            refresh((n) => n + 1);
          }}
        >
          Reiniciar
        </button>
        <label>
          Velocidade{' '}
          <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
            {[0.5, 1, 2, 4].map((v) => (
              <option key={v} value={v}>
                {v}×
              </option>
            ))}
          </select>
        </label>
        <label>
          <input type="checkbox" checked={reduced} onChange={(e) => setReduced(e.target.checked)} />{' '}
          Movimento reduzido
        </label>
      </div>
      <p className="sim-note">
        Almoxarifado: {s.units.filter((u) => u.location.startsWith('IN')).length} / 6 unidades ·
        Transportador: {s.trip ? `${s.trip.unit} → ${locationLabel(s.trip.to)}` : 'livre'}
      </p>
      <div className="sim-metrics">
        <div>
          <small>TEMPO SIMULADO</small>
          <strong>
            {s.time.toFixed(1)} <em>s</em>
          </strong>
        </div>
        <div>
          <small>APROVADAS</small>
          <strong>
            {s.units.filter((u) => u.location.startsWith('OUT')).length} <em>/ 6</em>
          </strong>
        </div>
        <div>
          <small>ESTOQUE AUXILIAR</small>
          <strong>
            {s.units.filter((u) => u.location.startsWith('B')).length} <em>/ 2 vagas</em>
          </strong>
        </div>
        <div>
          <small>REJEITADAS</small>
          <strong>{s.units.filter((u) => u.location.startsWith('REJ')).length}</strong>
        </div>
      </div>
      {s.status === 'blocked' && (
        <p role="alert">
          Sem destino livre ou evento futuro. Recursos ocupados:{' '}
          {s.units.map((u) => `${u.id} em ${locationLabel(u.location)}`).join('; ')}. Reinicie para
          restaurar o cenário.
        </p>
      )}
      <div className="sim-machines">
        {['M1', 'M2', 'M3'].map((m) => {
          const u = s.units.find((u) => u.location === m);
          return (
            <article key={m}>
              <span>{m}</span>
              <b>{u?.until ? 'Processando' : u ? 'Aguardando retirada' : 'Livre'}</b>
              <small>
                {u ? `${u.id} · Produto ${u.product}` : 'Pronta para receber'}
                {u?.until ? ` · ${(u.until - s.time).toFixed(1)} s` : ''}
              </small>
            </article>
          );
        })}
      </div>
      <div className="sim-details">
        <div>
          <h3>
            Unidades <small>Rastreabilidade local</small>
          </h3>
          <div className="sim-units">
            {s.units.map((u) => (
              <button key={u.id} aria-pressed={u.id === selected} onClick={() => setSelected(u.id)}>
                <i style={{ background: colors[u.product] }} />
                <span>
                  <b>{u.id}</b>
                  <small>
                    Produto {u.product} · {locationLabel(u.location)}
                  </small>
                </span>
                <span>
                  {u.step}/{u.recipe.length}
                </span>
              </button>
            ))}
          </div>
        </div>
        <article className="sim-history">
          <h3>
            {unit.id} <small>Produto {unit.product}</small>
          </h3>
          <p>
            {locationLabel(unit.location)} · Próxima etapa:{' '}
            {unit.location.startsWith('OUT')
              ? 'Concluída'
              : unit.location.startsWith('REJ')
                ? 'Rejeitada'
                : (unit.recipe[unit.step]?.machine ?? 'Validação')}
          </p>
          <p className="sim-route">
            {unit.recipe.map((r, i) => (
              <span key={i} className={i < unit.step ? 'done' : ''}>
                {r.machine} · {r.seconds}s
              </span>
            ))}
          </p>
          <ol>
            {unit.history.length ? (
              unit.history
                .slice()
                .reverse()
                .map((h, i) => <li key={i}>{h}</li>)
            ) : (
              <li>Aguardando entrada na linha.</li>
            )}
          </ol>
        </article>
      </div>
      <details className="sim-log">
        <summary>Histórico geral · {s.events.length} eventos</summary>
        <ol>
          {s.events
            .slice()
            .reverse()
            .map((e, i) => (
              <li key={i}>
                {e.time.toFixed(1)} s · {e.unit} · {e.text}
              </li>
            ))}
        </ol>
      </details>
      <p className="sim-note">
        Cenário local independente do planejador. Sem conexão com hardware. Tempos e mecanismos são
        ilustrativos.
      </p>
    </section>
  );
}
