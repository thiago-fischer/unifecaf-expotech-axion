import { useEffect, useRef, useState } from 'react';
import { request } from '../api/client';

export function ErrorNotice({ message }: { message: string }) {
  return message ? (
    <p className="notice error" role="alert">
      {message}
    </p>
  ) : null;
}

export function useList<T>(path: string) {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const sequence = useRef(0);
  async function reload() {
    const current = ++sequence.current;
    setLoading(true);
    setError('');
    try {
      const result = await request<T[]>(path);
      if (!Array.isArray(result)) throw new Error('A API enviou uma lista incompatível.');
      if (current === sequence.current) setData(result);
    } catch (error) {
      if (current === sequence.current) setError((error as Error).message);
    } finally {
      if (current === sequence.current) setLoading(false);
    }
  }
  useEffect(() => {
    void reload();
    return () => {
      sequence.current++;
    };
  }, [path]); // path define a fonte da lista.
  return { data, loading, error, reload };
}

export function positiveInteger(value: string): number {
  const result = Number(value);
  if (!value.trim() || !Number.isSafeInteger(result) || result <= 0)
    throw new Error('Informe números inteiros positivos.');
  return result;
}

export function validName(value: string): string {
  const result = value.trim();
  if (!result || result.length > 100) throw new Error('O nome deve conter de 1 a 100 caracteres.');
  return result;
}

export function ListState({
  loading,
  error,
  empty,
}: {
  loading: boolean;
  error: string;
  empty: boolean;
}) {
  return (
    <>
      <ErrorNotice message={error} />
      {loading ? (
        <p role="status">Carregando registros…</p>
      ) : !error && empty ? (
        <p className="empty">Nenhum registro cadastrado.</p>
      ) : null}
    </>
  );
}

export type Area = 'Máquinas' | 'Produtos' | 'Ordens' | 'Planejamento' | 'Simulação';
export type Navigate = (area: Area, orderId?: number) => void;
