import { useId, useState } from 'react';
import type { Plan } from '../api/types';

const colors = ['#236650', '#416fa3', '#8b5a91', '#a26728', '#477f83', '#9b4d59'];

export default function PlanningGantt({ plan }: { plan: Plan }) {
  const id = useId();
  const [active, setActive] = useState<string | null>(null);
  const products = new Map(
    plan.input_snapshot.items.map((item, index) => [
      item.product_id,
      {
        name: item.product_name,
        color: colors[index % colors.length],
      },
    ]),
  );
  const machines = plan.input_snapshot.machines;
  const width = 1000;
  const left = 200;
  const plotWidth = width - left - 24;
  const rowHeight = 64;
  const top = 36;
  const height = top + machines.length * rowHeight + 32;
  const scale = (time: number) => left + (time / plan.metrics.makespan_seconds) * plotWidth;
  const ticks = Array.from(
    { length: 6 },
    (_, index) => (plan.metrics.makespan_seconds * index) / 5,
  );

  return (
    <section className="gantt" aria-label="Gráfico de Gantt por máquina">
      <div className="gantt-legend" aria-label="Legenda de produtos">
        {[...products].map(([productId, product]) => (
          <span key={productId}>
            <i style={{ backgroundColor: product.color }} aria-hidden="true" />
            {product.name} · #{productId}
          </span>
        ))}
      </div>
      <div
        className="gantt-scroll"
        role="region"
        aria-label="Cronograma por máquina em segundos"
        tabIndex={0}
      >
        <svg
          role="group"
          viewBox={`0 0 ${width} ${height}`}
          aria-labelledby={`${id}-title ${id}-description`}
        >
          <title id={`${id}-title`}>Gantt da ordem #{plan.order_id}</title>
          <desc id={`${id}-description`}>
            Cada linha representa uma máquina. As barras representam operações, posicionadas pelo
            início e pela duração. Cores identificam produtos. Tempos em segundos.
          </desc>
          {machines.map((machine, index) => (
            <g key={machine.machine_id}>
              <rect
                x="0"
                y={top + index * rowHeight}
                width={width}
                height={rowHeight}
                fill={index % 2 ? '#ffffff' : '#f5f7f1'}
              />
              <text x="12" y={top + index * rowHeight + 28} className="gantt-machine">
                <title>
                  {machine.machine_name} · #{machine.machine_id}
                </title>
                {machine.machine_name.length > 24
                  ? `${machine.machine_name.slice(0, 23)}…`
                  : machine.machine_name}
              </text>
              <text x="12" y={top + index * rowHeight + 46} className="gantt-machine-id">
                Máquina #{machine.machine_id}
              </text>
            </g>
          ))}
          {ticks.map((time, index) => (
            <g key={index}>
              <line
                x1={scale(time)}
                x2={scale(time)}
                y1={top}
                y2={height - 26}
                className="gantt-grid"
              />
              <text
                x={scale(time)}
                y="22"
                textAnchor={index === 5 ? 'end' : 'middle'}
                className="gantt-tick"
              >
                {Number(time.toFixed(2)).toLocaleString('pt-BR')} s
              </text>
            </g>
          ))}
          {plan.operations.map((operation) => {
            const row = machines.findIndex(
              (machine) => machine.machine_id === operation.machine_id,
            );
            const product = products.get(operation.product_id);
            const machine = machines[row];
            const barWidth =
              (operation.duration_seconds / plan.metrics.makespan_seconds) * plotWidth;
            const label = `${operation.unit_id} · E${operation.step_sequence}`;
            const description = `${product?.name} · #${operation.product_id} | Unidade ${operation.unit_id} | Etapa ${operation.step_sequence} | ${machine?.machine_name} · #${operation.machine_id} | Início ${operation.start_seconds} s | Fim ${operation.end_seconds} s | Duração ${operation.duration_seconds} s`;
            return (
              <g
                key={operation.operation_id}
                tabIndex={0}
                role="img"
                aria-label={description}
                className="gantt-operation"
                onMouseEnter={() => setActive(description)}
                onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(description)}
                onBlur={() => setActive(null)}
              >
                <title>{description}</title>
                <rect
                  x={scale(operation.start_seconds)}
                  y={top + row * rowHeight + 14}
                  width={barWidth}
                  height="36"
                  rx="3"
                  fill={product?.color ?? colors[0]}
                />
                {barWidth > label.length * 6.5 + 12 && (
                  <text
                    x={scale(operation.start_seconds) + barWidth / 2}
                    y={top + row * rowHeight + 37}
                    textAnchor="middle"
                    className="gantt-bar-label"
                    aria-hidden="true"
                  >
                    {label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
      <p className="gantt-description">
        {active ||
          'Passe o cursor sobre uma operação ou use Tab para consultar seus detalhes. Cada barra representa uma etapa de uma unidade lógica.'}
      </p>
    </section>
  );
}
