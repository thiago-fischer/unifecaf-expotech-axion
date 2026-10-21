import type { Plan } from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    public status = 0,
    public retryAt = 0,
  ) {
    super(message);
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function retryDeadline(value: string | null): number {
  if (!value) return Date.now() + 1000;
  const seconds = Number(value);
  return Math.max(
    Date.now(),
    Number.isFinite(seconds) ? Date.now() + seconds * 1000 : Date.parse(value) || Date.now() + 1000,
  );
}

function errorMessage(body: unknown, status: number): string {
  if (status >= 500)
    return status === 503 && record(body) && body.code === 'planning_busy'
      ? 'Planejamento temporariamente ocupado. Aguarde para tentar novamente.'
      : 'O servidor não conseguiu concluir a operação. Tente novamente.';
  if (!record(body)) return `Não foi possível concluir a operação (HTTP ${status}).`;
  const details: string[] = [];
  if (typeof body.detail === 'string') details.push(body.detail);
  if (Array.isArray(body.detail)) {
    for (const error of body.detail)
      if (record(error)) {
        const location = Array.isArray(error.loc)
          ? error.loc.filter((x) => x !== 'body').join(' → ')
          : 'Entrada';
        details.push(`${location}: verifique o valor informado.`);
      }
  }
  if (Array.isArray(body.violations))
    for (const item of body.violations)
      if (record(item)) {
        details.push(`${item.field}: valor ${item.actual}; limite ${item.limit}.`);
      }
  for (const key of ['machine_ids', 'product_ids'])
    if (Array.isArray(body[key])) {
      details.push(`IDs ausentes: ${body[key].join(', ')}. Atualize o catálogo.`);
    }
  return details.join('\n') || `Não foi possível concluir a operação (HTTP ${status}).`;
}

export async function request<T>(path: string, body?: unknown, planning = false): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), planning ? 60_000 : 15_000);
  try {
    const response = await fetch(`/api${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      throw new ApiError(
        'O servidor enviou uma resposta ilegível. Confira a lista antes de reenviar um cadastro.',
        response.status,
      );
    }
    if (
      planning &&
      response.status === 409 &&
      record(data) &&
      data.code === 'optimality_not_proven' &&
      record(data.result)
    ) {
      return data.result as T;
    }
    if (!response.ok)
      throw new ApiError(
        errorMessage(data, response.status),
        response.status,
        response.status === 503 ? retryDeadline(response.headers.get('Retry-After')) : 0,
      );
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    const message = controller.signal.aborted
      ? 'Tempo de espera esgotado. O servidor pode continuar calculando.'
      : 'Não foi possível conectar à API. Verifique se o backend está em execução.';
    throw new ApiError(
      message +
        (body !== undefined && !planning
          ? ' Confira a lista antes de reenviar: o cadastro pode ter sido concluído.'
          : ''),
    );
  } finally {
    clearTimeout(timer);
  }
}

export async function planOrder(orderId: number, allowFeasible: boolean): Promise<Plan> {
  const result = await request<Plan>(
    `/orders/${orderId}/plan`,
    allowFeasible ? { optimality_policy: 'allow_feasible' } : {},
    true,
  );
  if (
    result.schema_version !== 1 ||
    result.order_id !== orderId ||
    result.execution_ready !== false ||
    !['optimal', 'feasible'].includes(result.quality) ||
    result.optimality_proven !== (result.quality === 'optimal') ||
    !['genetic_algorithm', 'cp_sat'].includes(result.selected_source) ||
    !result.metrics ||
    !result.proof ||
    !Array.isArray(result.operations) ||
    !Array.isArray(result.input_snapshot?.items) ||
    !Array.isArray(result.input_snapshot?.machines)
  ) {
    throw new ApiError('O resultado do planejamento tem formato incompatível.');
  }
  return result;
}
