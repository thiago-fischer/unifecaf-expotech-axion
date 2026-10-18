import { useEffect, useRef, useState } from 'react';
import { ApiError, planOrder } from '../api/client';
import type { Order, Plan } from '../api/types';
import { ErrorNotice, ListState, useList, type Navigate } from '../components/Common';

export default function Planning({
  initialOrder,
  navigate,
}: {
  initialOrder?: number;
  navigate: Navigate;
}) {
  const orders = useList<Order>('/orders');
  const [selected, setSelected] = useState(initialOrder ? String(initialOrder) : '');
  const [allowFeasible, setAllowFeasible] = useState(false);
  const [result, setResult] = useState<Plan | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [retryAt, setRetryAt] = useState(0);
  const [now, setNow] = useState(Date.now());
  const sequence = useRef(0);
  const locked = useRef(false);
  const wait = Math.max(0, Math.ceil((retryAt - now) / 1000));
  useEffect(() => {
    if (!retryAt) return;
    const timer = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(timer);
  }, [retryAt]);
  useEffect(
    () => () => {
      sequence.current++;
    },
    [],
  );

  async function calculate() {
    if (!selected || locked.current || Date.now() < retryAt) return;
    const current = ++sequence.current;
    locked.current = true;
    setBusy(true);
    setResult(null);
    setError('');
    try {
      const plan = await planOrder(Number(selected), allowFeasible);
      if (current === sequence.current) setResult(plan);
    } catch (error) {
      if (current === sequence.current) {
        setError((error as Error).message);
        if (error instanceof ApiError) {
          setRetryAt(error.retryAt);
          setNow(Date.now());
        }
      }
    } finally {
      locked.current = false;
      if (current === sequence.current) setBusy(false);
    }
  }
  const productNames = new Map(
    result?.input_snapshot.items.map((item) => [item.product_id, item.product_name]),
  );
  const machineNames = new Map(
    result?.input_snapshot.machines.map((machine) => [machine.machine_id, machine.machine_name]),
  );
  return (
    <>
      <section className="panel">
        <div className="panel-heading">
          <h2>Gerar planejamento</h2>
          <button
            className="secondary"
            disabled={orders.loading}
            onClick={() => void orders.reload()}
          >
            Atualizar ordens
          </button>
        </div>
        <p>Calcule a programação das operações para uma ordem registrada.</p>
        <ListState loading={orders.loading} error={orders.error} empty={false} />
        {!orders.loading && !orders.error && !orders.data.length && (
          <p className="notice">
            Crie uma ordem para calcular seu planejamento.{' '}
            <button className="text-button" onClick={() => navigate('Ordens')}>
              Ir para ordens
            </button>
          </p>
        )}
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void calculate();
          }}
        >
          <fieldset disabled={busy}>
            <label>
              Ordem de produção
              <select
                required
                value={selected}
                onChange={(event) => {
                  sequence.current++;
                  setSelected(event.target.value);
                  setResult(null);
                  setError('');
                }}
              >
                <option value="">Selecione uma ordem</option>
                {orders.data.map((order) => (
                  <option key={order.id} value={order.id}>
                    Ordem #{order.id} · {order.items.reduce((sum, item) => sum + item.quantity, 0)}{' '}
                    unidades
                  </option>
                ))}
              </select>
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={allowFeasible}
                onChange={(event) => {
                  setAllowFeasible(event.target.checked);
                  setResult(null);
                }}
              />
              Permitir resultado viável sem prova de ótimo
            </label>
            <p className="hint">
              Por padrão, a API exige prova de ótimo. O cálculo pode levar dezenas de segundos.
            </p>
            <button type="submit" disabled={!selected || wait > 0}>
              {busy
                ? 'Calculando planejamento…'
                : wait > 0
                  ? `Aguarde ${wait} s para tentar novamente`
                  : 'Calcular planejamento'}
            </button>
          </fieldset>
        </form>
        <ErrorNotice message={error} />
        {busy && <p role="status">Calculando planejamento. Aguarde a resposta da API.</p>}
      </section>
      {result && (
        <section className="panel" aria-label="Resultado do planejamento">
          <div className="panel-heading">
            <h2>Planejamento da ordem #{result.order_id}</h2>
            <span className={`badge ${result.quality}`}>
              {result.quality === 'optimal' ? 'Ótimo comprovado' : 'Viável, sem prova de ótimo'}
            </span>
          </div>
          <div className="metrics">
            <div>
              <small>Tempo total planejado</small>
              <strong>{result.metrics.makespan_seconds} s</strong>
            </div>
            <div>
              <small>Unidades lógicas</small>
              <strong>{result.metrics.unit_count}</strong>
            </div>
            <div>
              <small>Operações</small>
              <strong>{result.metrics.operation_count}</strong>
            </div>
          </div>
          <dl className="facts">
            <div>
              <dt>Prova de ótimo</dt>
              <dd>{result.optimality_proven ? 'Sim' : 'Não'}</dd>
            </div>
            <div>
              <dt>Origem do plano</dt>
              <dd>
                {result.selected_source === 'genetic_algorithm' ? 'Algoritmo Genético' : 'CP-SAT'}
              </dd>
            </div>
            <div>
              <dt>Método de prova</dt>
              <dd>
                {
                  { cp_sat: 'CP-SAT', analytical_bound: 'Limite analítico', none: 'Sem prova' }[
                    result.proof.method
                  ]
                }
              </dd>
            </div>
          </dl>
          <p className="notice">
            Planejamento em software; não habilita execução física. A prova se refere ao modelo
            simplificado, sem transporte e setup.
          </p>
          <h3>Operações planejadas</h3>
          <p className="hint">
            Tempos relativos ao início do plano, em segundos. As unidades são lógicas. O resultado é
            transitório e se perde ao sair desta área ou recarregar a página.
          </p>
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Tabela de operações">
            <table>
              <caption>Operações da ordem #{result.order_id}</caption>
              <thead>
                <tr>
                  {[
                    'Produto',
                    'Unidade',
                    'Etapa',
                    'Máquina',
                    'Início (s)',
                    'Fim (s)',
                    'Duração (s)',
                  ].map((label) => (
                    <th key={label} scope="col">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.operations.map((operation) => (
                  <tr key={operation.operation_id}>
                    <td>
                      {productNames.get(operation.product_id)} · #{operation.product_id}
                    </td>
                    <td>{operation.unit_id}</td>
                    <td>{operation.step_sequence}</td>
                    <td>
                      {machineNames.get(operation.machine_id)} · #{operation.machine_id}
                    </td>
                    <td>{operation.start_seconds}</td>
                    <td>{operation.end_seconds}</td>
                    <td>{operation.duration_seconds}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
