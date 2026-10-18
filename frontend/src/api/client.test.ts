import { describe, expect, it, vi } from 'vitest';
import { ApiError, planOrder, request, retryDeadline } from './client';
import { json, plan } from '../test/fixtures';

describe('Contrato HTTP do planejamento', () => {
  it.each(['optimal', 'feasible'] as const)(
    'aceita 200 %s e envia a política explícita',
    async (quality) => {
      const fetcher = vi.fn().mockResolvedValue(json(plan(quality)));
      vi.stubGlobal('fetch', fetcher);
      expect((await planOrder(17, quality === 'feasible')).quality).toBe(quality);
      expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual(
        quality === 'feasible' ? { optimality_policy: 'allow_feasible' } : {},
      );
    },
  );
  it('lê candidato em result de 409 sem repetir ou mudar política', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(json({ code: 'optimality_not_proven', result: plan('feasible') }, 409));
    vi.stubGlobal('fetch', fetcher);
    expect((await planOrder(17, false)).quality).toBe('feasible');
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('apresenta todas as violações de limite', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        json(
          {
            detail: 'Limites excedidos.',
            violations: [
              { field: 'unit_count', actual: 120, limit: 100 },
              { field: 'operation_count', actual: 1100, limit: 1000 },
            ],
          },
          422,
        ),
      ),
    );
    await expect(planOrder(17, false)).rejects.toThrow(
      'unit_count: valor 120; limite 100.\noperation_count: valor 1100; limite 1000.',
    );
  });
  it('preserva localização dos campos e IDs ausentes', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          json({ detail: [{ loc: ['body', 'items', 0, 'quantity'], msg: 'English' }] }, 422),
        )
        .mockResolvedValueOnce(json({ detail: 'Máquinas ausentes.', machine_ids: [23, 77] }, 422)),
    );
    await expect(request('/orders', {})).rejects.toThrow(
      'items → 0 → quantity: verifique o valor informado.',
    );
    await expect(request('/products', {})).rejects.toThrow('23, 77');
  });
  it('respeita Retry-After em segundos e data HTTP', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-17T12:00:00Z'));
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(json({ code: 'planning_busy' }, 503, { 'Retry-After': '4' })),
    );
    const error = await planOrder(17, false).catch((error) => error as ApiError);
    expect(error).toMatchObject({ status: 503, retryAt: Date.now() + 4000 });
    expect(retryDeadline('Sat, 17 Oct 2026 12:00:05 GMT')).toBe(Date.now() + 5000);
  });
  it.each([404, 409, 500])('trata HTTP %i como falha quando não há candidato', async (status) => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          json({ detail: status === 500 ? 'Detalhe privado' : 'Recurso não encontrado.' }, status),
        ),
    );
    await expect(planOrder(17, false)).rejects.toBeInstanceOf(ApiError);
    if (status === 500) await expect(planOrder(17, false)).rejects.not.toThrow('Detalhe privado');
  });
  it('distingue rede e confirmação incerta de cadastro', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(request('/machines', { name: 'A' })).rejects.toThrow(
      'Confira a lista antes de reenviar',
    );
    await expect(planOrder(17, false)).rejects.toThrow('conectar à API');
  });
  it('interrompe espera após 60 segundos', async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_path, options: RequestInit) =>
          new Promise((_resolve, reject) =>
            options.signal!.addEventListener('abort', () =>
              reject(new DOMException('Abortado', 'AbortError')),
            ),
          ),
      ),
    );
    const pending = expect(planOrder(17, false)).rejects.toThrow('Tempo de espera esgotado');
    await vi.advanceTimersByTimeAsync(60_000);
    await pending;
  });
  it('rejeita JSON ilegível e resultado incompatível', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(new Response('invalid'))
        .mockResolvedValueOnce(json({ ...plan(), order_id: 999 })),
    );
    await expect(planOrder(17, false)).rejects.toThrow('ilegível');
    await expect(planOrder(17, false)).rejects.toThrow('incompatível');
  });
});
