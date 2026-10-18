import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { Machines, Orders, Products } from './Catalog';
import { json } from '../test/fixtures';

it('gera sequências consecutivas após remover etapa e aceita revisitas', async () => {
  let sent: unknown;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (options.method === 'POST') {
        sent = JSON.parse(String(options.body));
        return json({ id: 71 }, 201);
      }
      return json(path.endsWith('/machines') ? [{ id: 63, name: 'Estação' }] : []);
    }),
  );
  render(<Products navigate={vi.fn()} />);
  await screen.findByRole('option', { name: 'Estação · #63' });
  await userEvent.type(screen.getByLabelText('Nome do produto'), 'Peça');
  await userEvent.selectOptions(screen.getByLabelText('Máquina da etapa 1'), '63');
  await userEvent.type(screen.getByLabelText('Duração da etapa 1 (s)'), '4');
  await userEvent.click(screen.getByRole('button', { name: 'Adicionar etapa' }));
  await userEvent.click(screen.getByRole('button', { name: 'Adicionar etapa' }));
  await userEvent.click(screen.getByRole('button', { name: 'Remover etapa 2' }));
  await userEvent.selectOptions(screen.getByLabelText('Máquina da etapa 2'), '63');
  await userEvent.type(screen.getByLabelText('Duração da etapa 2 (s)'), '7');
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar produto' }));
  await screen.findByText(/Produto cadastrado/);
  expect(sent).toEqual({
    name: 'Peça',
    steps: [
      { sequence: 1, machine_id: 63, processing_time_seconds: 4 },
      { sequence: 2, machine_id: 63, processing_time_seconds: 7 },
    ],
  });
});

it('impede produto repetido na seleção de itens', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) =>
      json(
        path.endsWith('/products')
          ? [
              { id: 41, name: 'Peça', steps: [] },
              { id: 77, name: 'Peça', steps: [] },
            ]
          : [],
      ),
    ),
  );
  render(<Orders navigate={vi.fn()} />);
  await screen.findByRole('option', { name: 'Peça · #41' });
  await userEvent.selectOptions(screen.getByLabelText('Produto do item 1'), '41');
  await userEvent.click(screen.getByRole('button', { name: 'Adicionar produto' }));
  expect(
    within(screen.getByLabelText('Produto do item 2')).getByRole('option', { name: 'Peça · #41' }),
  ).toBeDisabled();
  expect(
    within(screen.getByLabelText('Produto do item 2')).getByRole('option', { name: 'Peça · #77' }),
  ).toBeEnabled();
});

it('preserva nome após erro e permite recuperar catálogo sem tratar falha como vazio', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_path: string, options: RequestInit) =>
      options.method === 'POST' ? json({ detail: 'Nome inválido.' }, 422) : json([]),
    ),
  );
  render(<Machines />);
  await userEvent.type(screen.getByLabelText('Nome da máquina'), 'Estação');
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar máquina' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Nome inválido.');
  expect(screen.getByLabelText('Nome da máquina')).toHaveValue('Estação');
});
