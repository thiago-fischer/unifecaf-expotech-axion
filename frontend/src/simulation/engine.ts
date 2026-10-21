export type Step = { machine: string; seconds: number };
export type Unit = {
  id: string;
  product: string;
  expectedProduct: string;
  recipe: Step[];
  step: number;
  location: string;
  ready: number;
  until?: number;
  history: string[];
  completed: string[];
  rejected?: boolean;
};
export type Trip = {
  unit: string;
  from: string;
  to: string;
  start: number;
  approach: number;
  pickup: number;
  lifted: number;
  arrived: number;
  drop: number;
  end: number;
  originX: number;
};
export type State = {
  time: number;
  units: Unit[];
  trip?: Trip;
  x: number;
  events: { time: number; unit: string; text: string }[];
  status: 'ready' | 'active' | 'complete' | 'blocked';
};
export const positions: Record<string, number> = { M1: -4, M2: -1, M3: 2, B1: 4, B2: 5.3, QA: 7.3 };
for (let i = 0; i < 6; i++) {
  positions[`IN${i}`] = -10 + i * 0.8;
  positions[`OUT${i}`] = 9.5 + i * 0.8;
  positions[`REJ${i}`] = 15 + i * 0.8;
}
export const colors: Record<string, string> = { A: '#39d6bc', B: '#f6b44c', C: '#a79aff' };
export function createState(): State {
  const recipes: Record<string, Step[]> = {
    A: [
      { machine: 'M1', seconds: 6 },
      { machine: 'M2', seconds: 16 },
      { machine: 'M3', seconds: 5 },
    ],
    B: [
      { machine: 'M1', seconds: 4 },
      { machine: 'M3', seconds: 8 },
    ],
    C: [
      { machine: 'M3', seconds: 5 },
      { machine: 'M2', seconds: 30 },
    ],
  };
  return {
    time: 0,
    x: -10,
    events: [],
    status: 'ready',
    units: ['A', 'A', 'B', 'B', 'C', 'C'].map((product, i) => ({
      id: `MAT-00${i + 1}`,
      product,
      expectedProduct: product,
      recipe: recipes[product].map((s) => ({ ...s })),
      step: 0,
      location: `IN${i}`,
      ready: 0,
      history: [],
      completed: [],
    })),
  };
}
function log(s: State, u: Unit, text: string) {
  s.events.push({ time: s.time, unit: u.id, text });
  u.history.push(`${s.time.toFixed(1)} s · ${text}`);
}
function free(s: State, p: string) {
  return !s.units.some((u) => u.location === p) && s.trip?.to !== p;
}
function startOperation(s: State, u: Unit) {
  if (u.location === 'QA') {
    u.until = s.time + 2;
    log(s, u, 'Validação iniciada');
  } else if (u.recipe[u.step]?.machine === u.location) {
    u.until = s.time + u.recipe[u.step].seconds;
    log(s, u, `Processando ${u.location} · etapa ${u.step + 1}`);
  }
}
function dispatch(s: State) {
  if (s.trip) return;
  const rank = (u: Unit) =>
    u.location === 'QA' ? 0 : u.location.startsWith('M') ? 1 : u.location.startsWith('B') ? 2 : 3;
  const candidates = s.units
    .filter((u) => u.until === undefined && !/^(OUT|REJ|TRANS)/.test(u.location))
    .sort((a, b) => rank(a) - rank(b) || a.ready - b.ready || a.id.localeCompare(b.id));
  for (const u of candidates) {
    let to: string | undefined;
    if (u.location === 'QA') to = `${u.rejected ? 'REJ' : 'OUT'}${s.units.indexOf(u)}`;
    else {
      const next = u.recipe[u.step]?.machine ?? 'QA';
      if (free(s, next)) to = next;
      else if (u.location.startsWith('M')) to = ['B1', 'B2'].find((p) => free(s, p));
    }
    if (!to) continue;
    const approach = s.time + 0.3 + Math.abs(s.x - positions[u.location]) / 0.9;
    const pickup = approach + 0.6,
      lifted = pickup + 0.6,
      arrived = lifted + 0.3 + Math.abs(positions[u.location] - positions[to]) / 0.9;
    s.trip = {
      unit: u.id,
      from: u.location,
      to,
      start: s.time,
      approach,
      pickup,
      lifted,
      arrived,
      drop: arrived + 0.6,
      end: arrived + 1.2,
      originX: s.x,
    };
    log(s, u, `Transporte ${u.location} → ${to} · destino reservado`);
    return;
  }
  if (s.units.every((u) => /^(OUT|REJ)/.test(u.location))) s.status = 'complete';
  else if (!s.units.some((u) => u.until !== undefined)) s.status = 'blocked';
}
export function nextTime(s: State): number {
  const t = s.trip;
  return Math.min(
    ...s.units.flatMap((u) => (u.until === undefined ? [] : [u.until])),
    ...(t
      ? [t.approach, t.pickup, t.lifted, t.arrived, t.drop, t.end].filter((n) => n > s.time + 1e-8)
      : []),
  );
}
function settle(s: State) {
  // Stable order: operations by unit ID, transport phase, then dispatch.
  for (const u of s.units)
    if (u.until !== undefined && u.until <= s.time + 1e-8) {
      u.until = undefined;
      u.ready = s.time;
      if (u.location === 'QA') {
        u.rejected =
          u.id !== `MAT-00${s.units.indexOf(u) + 1}` ||
          u.product !== u.expectedProduct ||
          u.completed.join(',') !== u.recipe.map((r) => r.machine).join(',');
        log(
          s,
          u,
          u.rejected ? 'Rejeitada: identidade ou histórico inconsistente' : 'Validação aprovada',
        );
      } else {
        u.completed.push(u.location);
        u.step++;
        log(s, u, `Etapa concluída em ${u.location}`);
        if (u.recipe[u.step]?.machine === u.location) startOperation(s, u);
      }
    }
  const t = s.trip;
  if (t) {
    const u = s.units.find((u) => u.id === t.unit)!;
    if (s.time >= t.pickup - 1e-8 && s.time < t.end - 1e-8) u.location = 'TRANS';
    if (s.time >= t.end - 1e-8) {
      u.location = t.to;
      u.ready = s.time;
      s.x = positions[t.to];
      s.trip = undefined;
      log(s, u, `Entregue em ${t.to}`);
      startOperation(s, u);
    }
  }
  dispatch(s);
}
export function advance(s: State, delta: number) {
  if (s.status === 'complete' || s.status === 'blocked') return;
  s.status = 'active';
  settle(s);
  const target = s.time + delta;
  for (let i = 0; i < 10000; i++) {
    const n = nextTime(s);
    if (!Number.isFinite(n) || n > target + 1e-8) break;
    s.time = n;
    settle(s);
    if (s.status !== 'active') return;
  }
  s.time = target;
}
export function nextEvent(s: State) {
  advance(s, 0);
  const t = nextTime(s);
  if (Number.isFinite(t)) advance(s, t - s.time);
}
export function locationLabel(p: string) {
  return p.startsWith('IN')
    ? 'Almoxarifado'
    : p.startsWith('OUT')
      ? 'Saída'
      : p.startsWith('REJ')
        ? 'Rejeitados'
        : p === 'TRANS'
          ? 'Em transporte'
          : p === 'QA'
            ? 'Validação'
            : p.startsWith('B')
              ? `Estoque auxiliar · ${p}`
              : p;
}
export function pose(s: State) {
  const t = s.trip;
  if (!t) return { x: s.x, y: 3.4, carrying: false };
  const ease = (a: number, b: number) => {
    const p = Math.max(0, Math.min(1, (s.time - a) / (b - a)));
    return p * p * (3 - 2 * p);
  };
  const from = positions[t.from],
    to = positions[t.to];
  let x = from,
    y = 3.4;
  if (s.time < t.approach) x = t.originX + (from - t.originX) * ease(t.start, t.approach);
  else if (s.time < t.pickup) y = 3.4 - 2 * ease(t.approach, t.pickup);
  else if (s.time < t.lifted) y = 1.4 + 2 * ease(t.pickup, t.lifted);
  else if (s.time < t.arrived) x = from + (to - from) * ease(t.lifted, t.arrived);
  else {
    x = to;
    y = s.time < t.drop ? 3.4 - 2 * ease(t.arrived, t.drop) : 1.4 + 2 * ease(t.drop, t.end);
  }
  return { x, y, carrying: s.time >= t.pickup && s.time < t.drop };
}
