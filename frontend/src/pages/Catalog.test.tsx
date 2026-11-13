import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { Production } from './Catalog';
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
  render(<Production navigate={vi.fn()} />);
  await userEvent.click(screen.getByRole('button', { name: 'Novo produto' }));
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
  render(<Production navigate={vi.fn()} />);
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

it('preserva o formulário após erro de cadastro', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) =>
      options.method === 'POST'
        ? json({ detail: 'Nome inválido.' }, 422)
        : json(path.endsWith('/machines') ? [{ id: 63, name: 'Estação' }] : []),
    ),
  );
  render(<Production navigate={vi.fn()} />);
  await userEvent.click(screen.getByRole('button', { name: 'Novo produto' }));
  await screen.findByRole('option', { name: 'Estação · #63' });
  await userEvent.type(screen.getByLabelText('Nome do produto'), 'Peça');
  await userEvent.selectOptions(screen.getByLabelText('Máquina da etapa 1'), '63');
  await userEvent.type(screen.getByLabelText('Duração da etapa 1 (s)'), '7');
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar produto' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Nome inválido.');
  expect(screen.getByLabelText('Nome do produto')).toHaveValue('Peça');
});

it('limita a ordem a dez produtos distintos, com quantidade independente por linha', async () => {
  const products = Array.from({ length: 11 }, (_, index) => ({
    id: index + 1,
    name: 'Produto ' + (index + 1),
    steps: [],
  }));
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    if (options.method === 'POST') return json({ id: 13 }, 201);
    return json(path.endsWith('/products') ? products : []);
  });
  vi.stubGlobal('fetch', fetcher);
  const user = userEvent.setup();
  render(<Production navigate={vi.fn()} />);
  await screen.findByRole('option', { name: 'Produto 1 · #1' });
  const add = screen.getByRole('button', { name: 'Adicionar produto' });
  for (let index = 1; index < 10; index++) await user.click(add);
  expect(add).toBeDisabled();
  expect(screen.getByText('10 de 10 produtos')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Remover item 10' }));
  expect(add).toBeEnabled();
  await user.click(add);
  for (let index = 1; index <= 10; index++)
    await user.selectOptions(
      screen.getByLabelText('Produto do item ' + index, { exact: true }),
      String(index),
    );
  const quantity = screen.getByLabelText('Quantidade do item 1', { exact: true });
  await user.clear(quantity);
  await user.type(quantity, '12');
  await user.click(screen.getByRole('button', { name: 'Criar ordem' }));
  expect(await screen.findByText('Ordem #13 criada.')).toBeVisible();
  const post = fetcher.mock.calls.find(([, options]) => options.method === 'POST');
  expect(JSON.parse(String(post?.[1].body)).items).toHaveLength(10);
  expect(JSON.parse(String(post?.[1].body)).items[0]).toEqual({ product_id: 1, quantity: 12 });
});
