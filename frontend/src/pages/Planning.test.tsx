import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import Planning from './Planning';
import { json, plan } from '../test/fixtures';

function mockApi(response: () => Promise<Response>) {
  const fetcher = vi.fn((path: string) =>
    path.endsWith('/plan')
      ? response()
      : Promise.resolve(
          json([
            { id: 17, items: [{ product_id: 41, quantity: 1 }] },
            { id: 91, items: [] },
          ]),
        ),
  );
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}

it.each([200, 409])('exibe candidato viável em %i e nomes do snapshot', async (status) => {
  mockApi(async () =>
    json(
      status === 409
        ? { code: 'optimality_not_proven', result: plan('feasible') }
        : plan('feasible'),
      status,
    ),
  );
  render(<Planning initialOrder={17} navigate={vi.fn()} />);
  await screen.findByRole('option', { name: /Ordem #17/ });
  await userEvent.click(screen.getByRole('button', { name: 'Calcular planejamento' }));
  expect(await screen.findByText('Viável, sem prova de ótimo')).toBeVisible();
  expect(screen.getByText('Produto do snapshot · #41')).toBeVisible();
  expect(screen.getByText('Máquina do snapshot · #63')).toBeVisible();
  expect(screen.getByText(/não habilita execução física/)).toBeVisible();
  expect(screen.queryByText('Ótimo comprovado')).not.toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText('Ordem de produção'), '91');
  expect(
    screen.queryByRole('region', { name: 'Resultado do planejamento' }),
  ).not.toBeInTheDocument();
});

it('bloqueia envios repetidos durante cálculo e exige opção para allow_feasible', async () => {
  let resolve!: (value: Response) => void;
  const fetcher = mockApi(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  render(<Planning initialOrder={17} navigate={vi.fn()} />);
  await screen.findByRole('option', { name: /Ordem #17/ });
  const checkbox = screen.getByRole('checkbox');
  expect(checkbox).not.toBeChecked();
  await userEvent.click(checkbox);
  const button = screen.getByRole('button', { name: 'Calcular planejamento' });
  await userEvent.dblClick(button);
  expect(screen.getByRole('button', { name: 'Calculando planejamento…' })).toBeDisabled();
  expect(fetcher.mock.calls.filter(([path]) => path.endsWith('/plan'))).toHaveLength(1);
  await act(async () => resolve(json(plan())));
  expect(await screen.findByText('Ótimo comprovado')).toBeVisible();
});

it('aguarda Retry-After e só permite repetição manual', async () => {
  const fetcher = mockApi(async () => json({ code: 'planning_busy' }, 503, { 'Retry-After': '1' }));
  render(<Planning initialOrder={17} navigate={vi.fn()} />);
  await screen.findByRole('option', { name: /Ordem #17/ });
  vi.useFakeTimers();
  fireEvent.submit(screen.getByRole('button', { name: 'Calcular planejamento' }).closest('form')!);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  expect(screen.getByRole('button', { name: /Aguarde 1 s/ })).toBeDisabled();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1250);
  });
  expect(screen.getByRole('button', { name: 'Calcular planejamento' })).toBeEnabled();
  expect(fetcher.mock.calls.filter(([path]) => path.endsWith('/plan'))).toHaveLength(1);
});

it('descarta resposta recebida após sair da área', async () => {
  let resolve!: (value: Response) => void;
  mockApi(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const { unmount } = render(<Planning initialOrder={17} navigate={vi.fn()} />);
  await screen.findByRole('option', { name: /Ordem #17/ });
  await userEvent.click(screen.getByRole('button', { name: 'Calcular planejamento' }));
  unmount();
  render(<Planning initialOrder={91} navigate={vi.fn()} />);
  await act(async () => resolve(json(plan())));
  await waitFor(() => expect(screen.getByLabelText('Ordem de produção')).toHaveValue('91'));
  expect(screen.queryByText('Ótimo comprovado')).not.toBeInTheDocument();
});
