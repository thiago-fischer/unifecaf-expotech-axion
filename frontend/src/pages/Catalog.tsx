import { useRef, useState, type FormEvent } from 'react';
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

const maxProductsPerOrder = 10;
type List<T> = ReturnType<typeof useList<T>>;

function useSave<T extends { id: number }>(path: string, reload: () => Promise<void>) {
  const locked = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState<T>();

  async function save(build: () => unknown, clear: () => void) {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    setError('');
    setSaved(undefined);
    try {
      const result = await request<T>(path, build());
      clear();
      setSaved(result);
      await reload();
    } catch (error) {
      setError((error as Error).message);
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }
  return { busy, error, saved, save };
}

export function Production({ navigate }: { navigate: Navigate }) {
  const products = useList<Product>('/products');
  const machines = useList<Machine>('/machines');
  const orders = useList<Order>('/orders');
  const productNames = new Map(products.data.map(({ id, name }) => [id, name]));
  const machineNames = new Map(machines.data.map(({ id, name }) => [id, name]));

  return (
    <div className="production-layout">
      <div>
        <OrderForm
          products={products.data}
          ready={!products.loading && !products.error}
          reload={orders.reload}
          navigate={navigate}
        />
        <details className="panel">
          <summary>Ordens registradas</summary>
          <ListState loading={orders.loading} error={orders.error} empty={!orders.data.length} />
          {orders.error && (
            <button className="secondary" onClick={() => void orders.reload()}>
              Recarregar ordens
            </button>
          )}
          <ul className="records">
            {orders.data.map((order) => (
              <li key={order.id}>
                <details className="record-detail">
                  <summary>Ordem #{order.id}</summary>
                  <ul className="step-list">
                    {order.items.map(({ product_id, quantity }) => (
                      <li key={product_id}>
                        {productNames.get(product_id) ?? `Produto #${product_id}`} · {quantity} un.
                      </li>
                    ))}
                  </ul>
                  <div className="actions">
                    <button
                      className="secondary"
                      onClick={() => navigate('Planejamento', order.id)}
                    >
                      Planejar ordem #{order.id}
                    </button>
                    <button
                      className="secondary"
                      onClick={() => navigate('Maquete virtual', order.id)}
                    >
                      Simular ordem #{order.id}
                    </button>
                  </div>
                </details>
              </li>
            ))}
          </ul>
        </details>
      </div>
      <div>
        <ProductCatalog products={products} machines={machines} machineNames={machineNames} />
        <section className="panel" aria-labelledby="machine-catalog">
          <h2 id="machine-catalog">Máquinas cadastradas</h2>
          <ListState
            loading={machines.loading}
            error={machines.error}
            empty={!machines.data.length}
          />
          {machines.error && (
            <button className="secondary" onClick={() => void machines.reload()}>
              Recarregar máquinas
            </button>
          )}
          <ul className="records">
            {machines.data.map((machine) => (
              <li key={machine.id}>
                {machine.name} <small>#{machine.id}</small>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

function ProductCatalog({
  products,
  machines,
  machineNames,
}: {
  products: List<Product>;
  machines: List<Machine>;
  machineNames: Map<number, string>;
}) {
  const [editing, setEditing] = useState(false);

  return (
    <section className="panel" aria-labelledby="product-catalog">
      <div className="panel-heading">
        <h2 id="product-catalog">Produtos</h2>
        <button
          className="secondary"
          aria-expanded={editing}
          aria-controls="product-form"
          onClick={() => setEditing(!editing)}
        >
          {editing ? 'Fechar formulário' : 'Novo produto'}
        </button>
      </div>
      <div id="product-form" hidden={!editing}>
        <ProductForm machines={machines} reload={products.reload} />
      </div>
      <ListState loading={products.loading} error={products.error} empty={!products.data.length} />
      {products.error && (
        <button className="secondary" onClick={() => void products.reload()}>
          Recarregar produtos
        </button>
      )}
      <ul className="records">
        {products.data.map((product) => (
          <li key={product.id}>
            <details className="record-detail">
              <summary>
                {product.name} <small>#{product.id}</small>
              </summary>
              <ol className="step-list">
                {product.steps.map((step) => (
                  <li key={step.sequence}>
                    {machineNames.get(step.machine_id) ?? `Máquina #${step.machine_id}`} ·{' '}
                    {step.processing_time_seconds} s
                  </li>
                ))}
              </ol>
            </details>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ProductForm({
  machines,
  reload,
}: {
  machines: List<Machine>;
  reload: () => Promise<void>;
}) {
  const state = useSave<Product>('/products', reload);
  const [name, setName] = useState('');
  const nextKey = useRef(1);
  const [steps, setSteps] = useState([{ key: 0, machine: '', duration: '' }]);

  function updateStep(key: number, change: { machine?: string; duration?: string }) {
    setSteps(steps.map((step) => (step.key === key ? { ...step, ...change } : step)));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void state.save(
      () => ({
        name: validName(name),
        steps: steps.map(({ machine, duration }, index) => ({
          sequence: index + 1,
          machine_id: positiveInteger(machine),
          processing_time_seconds: positiveInteger(duration),
        })),
      }),
      () => {
        setName('');
        setSteps([{ key: nextKey.current++, machine: '', duration: '' }]);
      },
    );
  }

  return (
    <form className="product-form" onSubmit={submit}>
      {!machines.loading && !machines.data.length && (
        <p className="hint">A receita precisa de uma máquina cadastrada.</p>
      )}
      <fieldset
        disabled={
          state.busy || machines.loading || Boolean(machines.error) || !machines.data.length
        }
      >
        <label>
          Nome do produto
          <input
            required
            maxLength={100}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <h3>Etapas da receita</h3>
        {steps.map((step, index) => (
          <div className="form-row" key={step.key}>
            <label>
              <span className={index ? 'sr-only' : undefined}>Máquina</span>
              <select
                required
                aria-label={`Máquina da etapa ${index + 1}`}
                value={step.machine}
                onChange={(event) => updateStep(step.key, { machine: event.target.value })}
              >
                <option value="">Selecione</option>
                {machines.data.map(({ id, name }) => (
                  <option key={id} value={id}>
                    {name} · #{id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className={index ? 'sr-only' : undefined}>Duração (s)</span>
              <input
                required
                type="number"
                min="1"
                step="1"
                aria-label={`Duração da etapa ${index + 1} (s)`}
                value={step.duration}
                onChange={(event) => updateStep(step.key, { duration: event.target.value })}
              />
            </label>
            <button
              type="button"
              className="remove"
              aria-label={`Remover etapa ${index + 1}`}
              disabled={steps.length === 1}
              onClick={() => setSteps(steps.filter(({ key }) => key !== step.key))}
            >
              ×
            </button>
          </div>
        ))}
        <div className="actions">
          <button
            type="button"
            className="text-button"
            onClick={() =>
              setSteps([...steps, { key: nextKey.current++, machine: '', duration: '' }])
            }
          >
            <span aria-hidden="true">+</span> Adicionar etapa
          </button>
          <button type="submit">{state.busy ? 'Salvando…' : 'Cadastrar produto'}</button>
        </div>
      </fieldset>
      <ErrorNotice message={state.error} />
      {state.saved && (
        <p role="status" className="notice success">
          Produto cadastrado. ID: {state.saved.id}.
        </p>
      )}
    </form>
  );
}

function OrderForm({
  products,
  ready,
  reload,
  navigate,
}: {
  products: Product[];
  ready: boolean;
  reload: () => Promise<void>;
  navigate: Navigate;
}) {
  const state = useSave<Order>('/orders', reload);
  const nextKey = useRef(1);
  const [items, setItems] = useState([{ key: 0, product: '', quantity: '1' }]);
  const canAdd = items.length < Math.min(maxProductsPerOrder, products.length);

  function updateItem(key: number, change: { product?: string; quantity?: string }) {
    setItems(items.map((item) => (item.key === key ? { ...item, ...change } : item)));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void state.save(
      () => {
        const entries = items.map(({ product, quantity }) => ({
          product_id: positiveInteger(product),
          quantity: positiveInteger(quantity),
        }));
        if (new Set(entries.map(({ product_id }) => product_id)).size !== entries.length)
          throw new Error('Cada produto pode aparecer somente uma vez na ordem.');
        return { items: entries };
      },
      () => setItems([{ key: nextKey.current++, product: '', quantity: '1' }]),
    );
  }

  return (
    <section className="panel" aria-labelledby="new-order">
      <h2 id="new-order">Nova ordem de produção</h2>
      {ready && !products.length && (
        <p className="hint">Cadastre um produto para criar uma ordem.</p>
      )}
      <form onSubmit={submit}>
        <fieldset disabled={state.busy || !ready || !products.length}>
          {items.map((item, index) => (
            <div className="form-row" key={item.key}>
              <label>
                <span className={index ? 'sr-only' : undefined}>Produto</span>
                <select
                  required
                  aria-label={`Produto do item ${index + 1}`}
                  value={item.product}
                  onChange={(event) => updateItem(item.key, { product: event.target.value })}
                >
                  <option value="">Selecione um produto</option>
                  {products.map(({ id, name }) => (
                    <option
                      key={id}
                      value={id}
                      disabled={items.some(
                        (row) => row.key !== item.key && row.product === String(id),
                      )}
                    >
                      {name} · #{id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className={index ? 'sr-only' : undefined}>Quantidade</span>
                <input
                  required
                  type="number"
                  min="1"
                  step="1"
                  aria-label={`Quantidade do item ${index + 1}`}
                  value={item.quantity}
                  onChange={(event) => updateItem(item.key, { quantity: event.target.value })}
                />
              </label>
              <button
                type="button"
                className="remove"
                aria-label={`Remover item ${index + 1}`}
                disabled={items.length === 1}
                onClick={() => setItems(items.filter(({ key }) => key !== item.key))}
              >
                ×
              </button>
            </div>
          ))}
          <div className="actions order-actions">
            <button
              type="button"
              className="text-button"
              disabled={!canAdd}
              onClick={() => {
                if (canAdd)
                  setItems([...items, { key: nextKey.current++, product: '', quantity: '1' }]);
              }}
            >
              <span aria-hidden="true">+</span> Adicionar produto
            </button>
            <span className="hint" aria-live="polite">
              {items.length} de {maxProductsPerOrder} produtos
            </span>
            <button type="submit">{state.busy ? 'Salvando…' : 'Criar ordem'}</button>
          </div>
        </fieldset>
      </form>
      <ErrorNotice message={state.error} />
      {state.saved && (
        <div className="notice success">
          <span role="status">Ordem #{state.saved.id} criada.</span>
          <button className="text-button" onClick={() => navigate('Planejamento', state.saved?.id)}>
            Planejar agora
          </button>
        </div>
      )}
    </section>
  );
}
