import { useRef, useState } from 'react';
import { startExecution } from '../api/client';
import type { Machine, Order, Product } from '../api/types';
import { ErrorNotice, ListState, useList } from './Common';

const stations = ['M1', 'M2', 'M3'] as const;
type Station = (typeof stations)[number];
const defaultStations = new Map<string, Station>([
  ['Torno CNC', 'M1'],
  ['Fresadora CNC', 'M2'],
  ['Centro de Usinagem CNC', 'M3'],
]);

export default function ExecutionForm({
  initialOrder,
  available,
  onStart,
  onReset,
  resetting,
  canReset,
}: {
  initialOrder?: number;
  available: boolean;
  onStart: (id: string) => void;
  onReset: () => void;
  resetting: boolean;
  canReset: boolean;
}) {
  const orders = useList<Order>('/orders');
  const products = useList<Product>('/products');
  const machines = useList<Machine>('/machines');
  const [orderId, setOrderId] = useState(initialOrder ?? 0);
  const [choices, setChoices] = useState<Record<number, Station | ''>>({});
  const [allowFeasible, setAllowFeasible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const lock = useRef(false);
  const order = orders.data.find((item) => item.id === orderId);
  const catalog = new Map(products.data.map((item) => [item.id, item]));
  const machineIds = [
    ...new Set(
      order?.items.flatMap(
        ({ product_id }) =>
          catalog.get(product_id)?.steps.map(({ machine_id }) => machine_id) ?? [],
      ),
    ),
  ].sort((a, b) => a - b);
  const names = new Map(machines.data.map(({ id, name }) => [id, name]));
  const counts = new Map<Station, number>();
  for (const id of machineIds) {
    const station = defaultStations.get(names.get(id) ?? '');
    if (station) counts.set(station, (counts.get(station) ?? 0) + 1);
  }
  const rows = machineIds.map((id) => {
    const name = names.get(id) ?? `Máquina #${id}`;
    const suggested = defaultStations.get(name);
    return {
      id,
      name,
      station: choices[id] ?? (suggested && counts.get(suggested) === 1 ? suggested : ''),
    };
  });
  const mapped = rows.map(({ station }) => station);
  const loading = orders.loading || products.loading || machines.loading;
  const loadError = orders.error || products.error || machines.error;
  const total = order?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0;
  const issue =
    total > 10
      ? 'A maquete comporta até 10 peças por ordem.'
      : machineIds.length > 3
        ? 'A ordem usa mais de três máquinas de processamento.'
        : order &&
            !loading &&
            (!machineIds.length ||
              order.items.some(({ product_id }) => !catalog.get(product_id)?.steps.length) ||
              machineIds.some((id) => !names.has(id)))
          ? 'O catálogo não contém todas as receitas ou máquinas da ordem.'
          : mapped.filter(Boolean).length !== new Set(mapped.filter(Boolean)).size
            ? 'Selecione uma estação distinta para cada máquina.'
            : '';
  const canStart =
    available &&
    !loading &&
    !loadError &&
    Boolean(order) &&
    rows.length > 0 &&
    mapped.every(Boolean) &&
    !issue;

  async function submit() {
    if (!canStart || lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    try {
      const mapping = Object.fromEntries(
        rows.flatMap(({ id, station }) => (station ? [[id, station] as const] : [])),
      );
      const execution = await startExecution(orderId, mapping, allowFeasible);
      onStart(execution.id);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  return (
    <section className="panel" aria-label="Iniciar ordem simulada">
      <h3>Iniciar ordem simulada</h3>
      <ListState loading={loading} error={loadError} empty={!orders.data.length} />
      {loadError && (
        <button
          className="secondary"
          onClick={() => {
            void Promise.all([orders.reload(), products.reload(), machines.reload()]);
          }}
        >
          Recarregar catálogo
        </button>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <fieldset disabled={busy || loading || Boolean(loadError) || !available}>
          <label>
            Ordem de produção
            <select
              required
              value={orderId || ''}
              onChange={(event) => {
                setOrderId(Number(event.target.value));
                setChoices({});
                setError('');
              }}
            >
              <option value="">Selecione uma ordem</option>
              {orders.data.map((item) => (
                <option key={item.id} value={item.id}>
                  Ordem #{item.id} · {item.items.reduce((sum, entry) => sum + entry.quantity, 0)}{' '}
                  peças
                </option>
              ))}
            </select>
          </label>
          {rows.length <= 3 &&
            rows.map(({ id, name, station }) => (
              <label key={id}>
                Estação para {name} (#{id})
                <select
                  required
                  value={station}
                  onChange={(event) => {
                    setChoices({ ...choices, [id]: event.target.value as Station | '' });
                    setError('');
                  }}
                >
                  <option value="">Selecione uma estação</option>
                  {stations.map((station) => (
                    <option key={station}>{station}</option>
                  ))}
                </select>
              </label>
            ))}
          <label className="checkbox">
            <input
              type="checkbox"
              checked={allowFeasible}
              onChange={(event) => setAllowFeasible(event.target.checked)}
            />
            Permitir plano viável sem prova de ótimo
          </label>
          <button type="submit" disabled={!canStart}>
            {busy ? 'Calculando e iniciando…' : 'Iniciar simulação'}
          </button>
        </fieldset>
      </form>
      <div className="sim-controls">
        <button className="secondary" disabled={!canReset || resetting || busy} onClick={onReset}>
          {resetting ? 'Restaurando…' : 'Restaurar maquete'}
        </button>
      </div>
      <ErrorNotice message={issue || error} />
      {busy && <p role="status">Calculando a programação da ordem…</p>}
    </section>
  );
}
