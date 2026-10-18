import type { Plan } from '../api/types';

export function plan(quality: Plan['quality'] = 'optimal'): Plan {
  return {
    schema_version: 1,
    order_id: 17,
    quality,
    optimality_proven: quality === 'optimal',
    selected_source: 'genetic_algorithm',
    execution_ready: false,
    metrics: { makespan_seconds: 8, unit_count: 1, operation_count: 1 },
    proof: { method: quality === 'optimal' ? 'analytical_bound' : 'none' },
    input_snapshot: {
      items: [{ product_id: 41, product_name: 'Produto do snapshot' }],
      machines: [{ machine_id: 63, machine_name: 'Máquina do snapshot' }],
    },
    operations: [
      {
        operation_id: 'o17-p41-u1-s1',
        unit_id: 'o17-p41-u1',
        product_id: 41,
        step_sequence: 1,
        machine_id: 63,
        start_seconds: 0,
        end_seconds: 8,
        duration_seconds: 8,
      },
    ],
  };
}

export function json(body: unknown, status = 200, headers?: Record<string, string>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}
