import { useEffect, useRef, useState } from 'react';
import { request } from '../api/client';
import ExecutionForm from '../components/ExecutionForm';
import { ErrorNotice } from '../components/Common';
import Scene from '../simulation/Scene';
import { initialScene, locationLabel, type State } from '../simulation/sceneState';
import { liveState, type LiveStatus } from '../simulation/live';
import '../simulation/simulation.css';

const speeds = [0.5, 1, 2, 4];

export default function Simulation({ initialOrder }: { initialOrder?: number }) {
  const state = useRef<State>(initialScene());
  const [snapshot, setSnapshot] = useState<LiveStatus | null>(null);
  const [offline, setOffline] = useState(false);
  const [selected, setSelected] = useState('');
  const unitDetails = useRef<HTMLDetailsElement>(null);

  function selectUnit(id: string) {
    setSelected(id);
    if (id && unitDetails.current) unitDetails.current.open = true;
  }
  const [camera, setCamera] = useState(0);
  const [startingId, setStartingId] = useState('');
  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState('');
  const [pendingSpeed, setPendingSpeed] = useState<number | null>(null);
  const [speedError, setSpeedError] = useState('');
  const resetGeneration = useRef(0);
  const [reduced, setReduced] = useState(
    () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false,
  );
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function update() {
      const generation = resetGeneration.current;
      let delay = 750;
      try {
        const next = await request<LiveStatus>('/simulation/status');
        if (!active || generation !== resetGeneration.current) return;
        if (
          next.execution?.state === 'running' ||
          next.execution?.state === 'queued' ||
          next.mesa.movimento ||
          next.mesa.progresso_cabecote > 0
        )
          delay = 100;
        state.current = liveState(next);
        setSnapshot(next);
        setOffline(false);
      } catch {
        if (active && generation === resetGeneration.current) setOffline(true);
      } finally {
        if (active) timer = setTimeout(update, delay);
      }
    }
    void update();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, []);

  const execution = snapshot?.execution;
  const waitingForRun = Boolean(startingId && execution?.id !== startingId);
  useEffect(() => {
    if (!startingId) return;
    if (execution?.id === startingId) {
      setStartingId('');
      return;
    }
    const timeout = setTimeout(() => setStartingId(''), 5000);
    return () => clearTimeout(timeout);
  }, [startingId, execution?.id]);
  const active = execution?.state === 'queued' || execution?.state === 'running';
  const canReset =
    Boolean(snapshot) && !offline && !active && !waitingForRun && pendingSpeed === null;

  async function changeSpeed(speed: number) {
    setPendingSpeed(speed);
    setSpeedError('');
    try {
      await request<void>('/simulation/speed', { velocidade: speed });
      resetGeneration.current++;
      setSnapshot((current) => current && { ...current, velocidade: speed });
    } catch (error) {
      setSpeedError((error as Error).message);
    } finally {
      setPendingSpeed(null);
    }
  }

  async function resetSimulation() {
    if (!canReset || resetting) return;
    setResetting(true);
    setResetError('');
    try {
      await request<void>('/simulation/reset', {});
      resetGeneration.current++;
      setSnapshot(null);
      setSelected('');
      state.current = initialScene();
    } catch (error) {
      setResetError((error as Error).message);
    } finally {
      setResetting(false);
    }
  }
  const states = {
    queued: 'Aguardando início',
    running: 'Em execução',
    completed: 'Ciclo concluído',
    interrupted: 'Execução interrompida',
  };
  const status = offline
    ? 'Sem comunicação com o controlador'
    : resetting
      ? 'Restaurando maquete…'
      : waitingForRun
        ? 'Aguardando início'
        : execution
          ? states[execution.state]
          : snapshot
            ? 'Aguardando uma OP'
            : 'Conectando…';
  const units = state.current.units;
  const selectedUnit = units.find((unit) => unit.id === selected);
  const rejection = selectedUnit && execution?.rejected_units[selectedUnit.product];
  return (
    <section className="simulation" aria-label="Execução da maquete pelo servidor">
      <div className="sim-top">
        <span>{execution ? `Ordem #${execution.order_id}` : 'Controlador simulado'}</span>
        <span className="sim-status" data-connected={Boolean(snapshot) && !offline} role="status">
          {status}
        </span>
      </div>
      {execution?.reason && <p role="alert">{execution.reason}</p>}
      {snapshot?.falhas.map((failure, i) => (
        <p role="alert" key={i}>
          {failure.mensagem}
        </p>
      ))}
      <div className="sim-layout">
        <div className="sim-stage">
          <Scene state={state} select={selectUnit} reset={camera} reduced={reduced} />
          <div className="sim-stage-bottom">
            <span>Arraste para orbitar · Role para aproximar</span>
            <button onClick={() => setCamera((n) => n + 1)}>Restaurar câmera</button>
          </div>
        </div>
        <div>
          {' '}
          <ExecutionForm
            initialOrder={initialOrder}
            available={canReset && !resetting && !snapshot?.falhas.length}
            onStart={setStartingId}
            onReset={() => void resetSimulation()}
            resetting={resetting}
            canReset={canReset}
          />
          <ErrorNotice message={resetError} />
          {canReset && units.some((unit) => unit.location.startsWith('OUT')) && (
            <p>Use Restaurar maquete para devolver os cubos à esteira de entrada.</p>
          )}
        </div>
      </div>
      {execution && (
        <div className="sim-metrics">
          <div>
            <small>Operações concluídas</small>
            <strong>{execution.completed_operations.length}</strong>
          </div>
          <div>
            <small>Peças aprovadas</small>
            <strong>{execution.approved_units.length}</strong>
          </div>
          <div>
            <small>Peças rejeitadas</small>
            <strong>{Object.keys(execution.rejected_units).length}</strong>
          </div>
          <div>
            <small>Estoque auxiliar</small>
            <strong>
              {units.filter((unit) => /^B[12]$/.test(unit.location)).length} <em>/ 2</em>
            </strong>
          </div>
        </div>
      )}
      <div className="sim-controls">
        <label>
          Velocidade{' '}
          <select
            disabled={!snapshot || offline || resetting || pendingSpeed !== null}
            value={pendingSpeed ?? snapshot?.velocidade ?? 1}
            onChange={(event) => void changeSpeed(Number(event.target.value))}
          >
            {speeds.map((speed) => (
              <option key={speed} value={speed}>
                {speed.toLocaleString('pt-BR')}×
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={reduced} onChange={(e) => setReduced(e.target.checked)} />{' '}
          Movimento reduzido
        </label>
      </div>
      <ErrorNotice message={speedError} />
      {snapshot && (
        <details className="panel" ref={unitDetails}>
          <summary>Estações e peças</summary>
          <div className="sim-machines">
            {Object.entries(state.current.live.machines).map(([name, machine]) => (
              <article key={name}>
                <span>{name}</span>
                <b>{machine.estado.replaceAll('_', ' ')}</b>
                {machine.tempo_restante_ms !== null && (
                  <small>{(machine.tempo_restante_ms / 1000).toFixed(1)} s restantes</small>
                )}
              </article>
            ))}
          </div>
          <div className="sim-units">
            {units.map((unit) => (
              <button
                key={unit.id}
                aria-pressed={selected === unit.id}
                onClick={() => setSelected(unit.id)}
              >
                <span>
                  <b>
                    {unit.id}
                    {unit.product ? ` · ${unit.product}` : ''}
                  </b>
                  <small>
                    {locationLabel(unit.location)}
                    {unit.reviewed ? (unit.rejected ? ' · Rejeitada' : ' · Aprovada') : ''}
                  </small>
                </span>
              </button>
            ))}
          </div>
          {rejection && <p role="status">{rejection}</p>}
        </details>
      )}
    </section>
  );
}
