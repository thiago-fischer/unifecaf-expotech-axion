import { useRef, useState, type ReactNode } from 'react';
import { request } from '../api/client';
import type { Machine, Order, Product } from '../api/types';
import {
  ErrorNotice,
  ListState,
  positiveInteger,
  useList,
  validName,
  type Navigate,
} from '../components/Common';

function useSave<T>(path: string, reload: () => Promise<void>) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const locked = useRef(false);
  async function save(build: () => unknown, clear: () => void, message: string) {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      const result = await request<T & { id: number }>(path, build());
      clear();
      setSuccess(`${message} ID: ${result.id}.`);
      await reload();
    } catch (error) {
      setError((error as Error).message);
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }
  return { busy, error, success, save };
}

function SaveStatus({ error, success }: { error: string; success: string }) {
  return (
    <>
      <ErrorNotice message={error} />
      {success && (
        <p className="notice success" role="status">
          {success}
        </p>
      )}
    </>
  );
}

function useDetail<T>(path: string) {
  const [detail, setDetail] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const sequence = useRef(0);
  async function open(id: number) {
    const current = ++sequence.current;
    setDetail(null);
    setError('');
    setLoading(true);
    try {
      const result = await request<T>(`${path}/${id}`);
      if (current === sequence.current) setDetail(result);
    } catch (error) {
      if (current === sequence.current) setError((error as Error).message);
    } finally {
      if (current === sequence.current) setLoading(false);
    }
  }
  function close() {
    sequence.current++;
    setDetail(null);
    setError('');
    setLoading(false);
  }
  return { detail, error, loading, open, close };
}

function Detail({
  state,
  children,
}: {
  state: ReturnType<typeof useDetail<unknown>>;
  children: ReactNode;
}) {
  if (!state.detail && !state.error && !state.loading) return null;
  return (
    <section className="panel detail" aria-label="Consulta individual">
      <div className="panel-heading">
        <h2>Consulta individual</h2>
        <button className="secondary" onClick={state.close}>
          Voltar à lista
        </button>
      </div>
      <ErrorNotice message={state.error} />
      {state.loading && <p role="status">Consultando registro…</p>}
      {children}
    </section>
  );
}

export function Machines() {
  const list = useList<Machine>('/machines');
  const state = useSave<Machine>('/machines', list.reload);
  const detail = useDetail<Machine>('/machines');
  const [name, setName] = useState('');
  return (
    <>
      <div className="columns">
        <section className="panel">
          <h2>Nova máquina</h2>
          <p>Cadastre uma estação para utilizar nas receitas.</p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void state.save(
                () => ({ name: validName(name) }),
                () => setName(''),
                'Máquina cadastrada.',
              );
            }}
          >
            <fieldset disabled={state.busy}>
              <label>
                Nome da máquina
                <input
                  required
                  maxLength={100}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Ex.: Torno CNC"
                />
              </label>
              <button type="submit">{state.busy ? 'Salvando…' : 'Cadastrar máquina'}</button>
            </fieldset>
          </form>
          <SaveStatus {...state} />
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Catálogo de máquinas</h2>
            <button
              className="secondary"
              disabled={list.loading}
              onClick={() => void list.reload()}
            >
              Atualizar
            </button>
          </div>
          <ListState loading={list.loading} error={list.error} empty={!list.data.length} />
          <ul className="records">
            {list.data.map((machine) => (
              <li key={machine.id}>
                <div>
                  <strong>{machine.name}</strong>
                  <small>Máquina #{machine.id}</small>
                </div>
                <button className="secondary" onClick={() => void detail.open(machine.id)}>
                  Consultar #{machine.id}
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
      <Detail state={detail}>
        {detail.detail && (
          <>
            <h3>{detail.detail.name}</h3>
            <p>Máquina #{detail.detail.id}</p>
          </>
        )}
      </Detail>
    </>
  );
}

export function Products({ navigate }: { navigate: Navigate }) {
  const list = useList<Product>('/products');
  const machines = useList<Machine>('/machines');
  const state = useSave<Product>('/products', list.reload);
  const detail = useDetail<Product>('/products');
  const [name, setName] = useState('');
  const nextKey = useRef(1);
  const initial = () => [{ key: nextKey.current++, machine: '', duration: '' }];
  const [steps, setSteps] = useState(initial);
  const machineName = (id: number) =>
    machines.data.find((machine) => machine.id === id)?.name || 'Máquina';
  return (
    <>
      <div className="columns">
        <section className="panel">
          <h2>Novo produto</h2>
          <p>Defina a sequência e o tempo de cada etapa.</p>
          <ListState loading={machines.loading} error={machines.error} empty={false} />
          <button
            className="text-button"
            disabled={machines.loading}
            onClick={() => void machines.reload()}
          >
            Atualizar máquinas disponíveis
          </button>
          {!machines.loading && !machines.error && !machines.data.length && (
            <p className="notice">
              Cadastre uma máquina para montar a receita.{' '}
              <button className="text-button" onClick={() => navigate('Máquinas')}>
                Ir para máquinas
              </button>
            </p>
          )}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void state.save(
                () => ({
                  name: validName(name),
                  steps: steps.map((step, index) => ({
                    sequence: index + 1,
                    machine_id: positiveInteger(step.machine),
                    processing_time_seconds: positiveInteger(step.duration),
                  })),
                }),
                () => {
                  setName('');
                  setSteps(initial());
                },
                'Produto cadastrado.',
              );
            }}
          >
            <fieldset disabled={state.busy || !machines.data.length}>
              <label>
                Nome do produto
                <input
                  required
                  maxLength={100}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Ex.: Suporte usinado"
                />
              </label>
              <div className="recipe">
                {steps.map((step, index) => (
                  <div className="recipe-step" key={step.key}>
                    <div className="panel-heading">
                      <h3>Etapa {index + 1}</h3>
                      <button
                        type="button"
                        className="text-button"
                        disabled={steps.length === 1}
                        aria-label={`Remover etapa ${index + 1}`}
                        onClick={() => setSteps(steps.filter((item) => item.key !== step.key))}
                      >
                        Remover
                      </button>
                    </div>
                    <label>
                      Máquina da etapa {index + 1}
                      <select
                        required
                        value={step.machine}
                        onChange={(event) =>
                          setSteps(
                            steps.map((item) =>
                              item.key === step.key
                                ? { ...item, machine: event.target.value }
                                : item,
                            ),
                          )
                        }
                      >
                        <option value="">Selecione uma máquina</option>
                        {machines.data.map((machine) => (
                          <option key={machine.id} value={machine.id}>
                            {machine.name} · #{machine.id}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Duração da etapa {index + 1} (s)
                      <input
                        required
                        type="number"
                        min="1"
                        step="1"
                        value={step.duration}
                        onChange={(event) =>
                          setSteps(
                            steps.map((item) =>
                              item.key === step.key
                                ? { ...item, duration: event.target.value }
                                : item,
                            ),
                          )
                        }
                      />
                    </label>
                  </div>
                ))}
              </div>
              <div className="actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setSteps([...steps, ...initial()])}
                >
                  Adicionar etapa
                </button>
                <button type="submit">{state.busy ? 'Salvando…' : 'Cadastrar produto'}</button>
              </div>
            </fieldset>
          </form>
          <SaveStatus {...state} />
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Catálogo de produtos</h2>
            <button
              className="secondary"
              disabled={list.loading}
              onClick={() => void list.reload()}
            >
              Atualizar
            </button>
          </div>
          <ListState loading={list.loading} error={list.error} empty={!list.data.length} />
          <ul className="records">
            {list.data.map((product) => (
              <li key={product.id}>
                <div>
                  <strong>{product.name}</strong>
                  <small>
                    Produto #{product.id} · {product.steps.length} etapas
                  </small>
                </div>
                <button className="secondary" onClick={() => void detail.open(product.id)}>
                  Consultar #{product.id}
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
      <Detail state={detail}>
        {detail.detail && (
          <>
            <h3>
              {detail.detail.name} · #{detail.detail.id}
            </h3>
            <ol className="step-list">
              {detail.detail.steps.map((step) => (
                <li key={step.sequence}>
                  {machineName(step.machine_id)} #{step.machine_id} · {step.processing_time_seconds}{' '}
                  s
                </li>
              ))}
            </ol>
          </>
        )}
      </Detail>
    </>
  );
}

export function Orders({ navigate }: { navigate: Navigate }) {
  const list = useList<Order>('/orders');
  const products = useList<Product>('/products');
  const state = useSave<Order>('/orders', list.reload);
  const detail = useDetail<Order>('/orders');
  const nextKey = useRef(1);
  const initial = () => [{ key: nextKey.current++, product: '', quantity: '' }];
  const [items, setItems] = useState(initial);
  const productName = (id: number) =>
    products.data.find((product) => product.id === id)?.name || 'Produto';
  const orderItems = (order: Order) => (
    <ul className="step-list">
      {order.items.map((item) => (
        <li key={item.product_id}>
          {productName(item.product_id)} #{item.product_id} · {item.quantity} un.
        </li>
      ))}
    </ul>
  );
  return (
    <>
      <div className="columns">
        <section className="panel">
          <h2>Nova ordem</h2>
          <p>Registre os produtos e as quantidades solicitadas.</p>
          <ListState loading={products.loading} error={products.error} empty={false} />
          <button
            className="text-button"
            disabled={products.loading}
            onClick={() => void products.reload()}
          >
            Atualizar produtos disponíveis
          </button>
          {!products.loading && !products.error && !products.data.length && (
            <p className="notice">
              Cadastre um produto antes de criar uma ordem.{' '}
              <button className="text-button" onClick={() => navigate('Produtos')}>
                Ir para produtos
              </button>
            </p>
          )}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void state.save(
                () => {
                  const result = items.map((item) => ({
                    product_id: positiveInteger(item.product),
                    quantity: positiveInteger(item.quantity),
                  }));
                  if (new Set(result.map((item) => item.product_id)).size !== result.length)
                    throw new Error('Cada produto pode aparecer somente uma vez na ordem.');
                  return { items: result };
                },
                () => setItems(initial()),
                'Ordem registrada como demanda; a produção não foi iniciada.',
              );
            }}
          >
            <fieldset disabled={state.busy || !products.data.length}>
              {items.map((item, index) => (
                <div className="recipe-step" key={item.key}>
                  <div className="panel-heading">
                    <h3>Item {index + 1}</h3>
                    <button
                      type="button"
                      className="text-button"
                      disabled={items.length === 1}
                      aria-label={`Remover item ${index + 1}`}
                      onClick={() => setItems(items.filter((row) => row.key !== item.key))}
                    >
                      Remover
                    </button>
                  </div>
                  <label>
                    Produto do item {index + 1}
                    <select
                      required
                      value={item.product}
                      onChange={(event) =>
                        setItems(
                          items.map((row) =>
                            row.key === item.key ? { ...row, product: event.target.value } : row,
                          ),
                        )
                      }
                    >
                      <option value="">Selecione um produto</option>
                      {products.data.map((product) => (
                        <option
                          key={product.id}
                          value={product.id}
                          disabled={items.some(
                            (row) => row.key !== item.key && row.product === String(product.id),
                          )}
                        >
                          {product.name} · #{product.id}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Quantidade do item {index + 1}
                    <input
                      required
                      type="number"
                      min="1"
                      step="1"
                      value={item.quantity}
                      onChange={(event) =>
                        setItems(
                          items.map((row) =>
                            row.key === item.key ? { ...row, quantity: event.target.value } : row,
                          ),
                        )
                      }
                    />
                  </label>
                </div>
              ))}
              <div className="actions">
                <button
                  type="button"
                  className="secondary"
                  disabled={items.length >= products.data.length}
                  onClick={() => setItems([...items, ...initial()])}
                >
                  Adicionar produto
                </button>
                <button type="submit">{state.busy ? 'Salvando…' : 'Criar ordem'}</button>
              </div>
            </fieldset>
          </form>
          <SaveStatus {...state} />
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Ordens registradas</h2>
            <button
              className="secondary"
              disabled={list.loading}
              onClick={() => void list.reload()}
            >
              Atualizar
            </button>
          </div>
          <ListState loading={list.loading} error={list.error} empty={!list.data.length} />
          <ul className="records">
            {list.data.map((order) => (
              <li key={order.id}>
                <div>
                  <strong>Ordem #{order.id}</strong>
                  {orderItems(order)}
                </div>
                <button className="secondary" onClick={() => void detail.open(order.id)}>
                  Consultar #{order.id}
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
      <Detail state={detail}>
        {detail.detail && (
          <>
            <h3>Ordem #{detail.detail.id}</h3>
            {orderItems(detail.detail)}
            <p>Demanda registrada. Sem reserva de máquinas ou execução física.</p>
            <button onClick={() => navigate('Planejamento', detail.detail!.id)}>
              Planejar ordem #{detail.detail.id}
            </button>
          </>
        )}
      </Detail>
    </>
  );
}
