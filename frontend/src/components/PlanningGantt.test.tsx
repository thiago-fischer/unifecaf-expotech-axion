import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import PlanningGantt from './PlanningGantt';
import { plan } from '../test/fixtures';

it('representa paralelismo, espera e revisita na escala comum de tempo', async () => {
  const result = plan();
  result.metrics.makespan_seconds = 20;
  result.input_snapshot.machines.push({ machine_id: 99, machine_name: 'Segunda máquina' });
  const first = { ...result.operations[0], duration_seconds: 4, end_seconds: 4 };
  result.operations = [
    first,
    { ...first, operation_id: 'parallel', machine_id: 99, end_seconds: 8, duration_seconds: 8 },
    {
      ...first,
      operation_id: 'revisit',
      step_sequence: 2,
      start_seconds: 10,
      end_seconds: 20,
      duration_seconds: 10,
    },
  ];
  render(<PlanningGantt plan={result} />);
  const operations = screen.getAllByRole('img');
  expect(operations).toHaveLength(3);
  const bars = operations.map((operation) => operation.querySelector('rect')!);
  expect(bars[0].getAttribute('x')).toBe('200');
  expect(bars[1].getAttribute('x')).toBe(bars[0].getAttribute('x'));
  expect(bars[1].getAttribute('y')).not.toBe(bars[0].getAttribute('y'));
  expect(bars[2].getAttribute('y')).toBe(bars[0].getAttribute('y'));
  expect(Number(bars[2].getAttribute('x'))).toBe(588);
  expect(Number(bars[2].getAttribute('width'))).toBe(388);
  expect(bars[2].getAttribute('fill')).toBe(bars[0].getAttribute('fill'));
  expect(operations[2]).toHaveAccessibleName(/Etapa 2.*Início 10 s.*Fim 20 s.*Duração 10 s/);
  await userEvent.tab(); // Região rolável.
  await userEvent.tab(); // Primeira operação.
  expect(operations[0]).toHaveFocus();
  expect(
    screen.getByText(/Produto do snapshot.*Início 0 s.*Duração 4 s/, { selector: 'p' }),
  ).toBeVisible();
});
