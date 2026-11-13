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
  reviewed?: boolean;
};
export type Trip = {
  unit: string;
  from: string;
  to: string;
  start: number;
  approach: number;
  pickup: number;
  lifted: number;
  scanStart?: number;
  scanEnd?: number;
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
  live?: {
    session: string;
    pose: { x: number; y: number; carrying: boolean };
    poseAt: (now: number) => { x: number; y: number; carrying: boolean };
    movingUntil: number;
    rfid: string | null;
    machines: Record<string, { estado: string; tempo_restante_ms: number | null }>;
  };
};
export const RFID_SCAN_DURATION = 0.01;
export const positions: Record<string, number> = {
  IN: -10,
  B1: -8.5,
  B2: -7.2,
  M1: -4,
  M2: -1,
  M3: 2,
  QA: 5,
  OUT: 7.6,
};
export const stationWidth = 2.4;
export const bufferWidth = 0.68;
const bufferRightEdge = positions.B2 + bufferWidth / 2;
const firstStationLeftEdge = positions.M1 - stationWidth / 2;
export const RFID_POSITION = (bufferRightEdge + firstStationLeftEdge) / 2;
export const conveyorCapacity = 10;
export const conveyorPitch = 0.8;

export function positionX(location: string) {
  if (location.startsWith('IN')) return positions.IN;
  if (location.startsWith('OUT')) return positions.OUT;
  return positions[location];
}

export function conveyorProgress(s: State) {
  const t = s.trip;
  if (!t) return { input: 0, output: 0 };
  const progress = (start: number) => Math.max(0, Math.min(1, (s.time - start) / 0.5));
  return {
    input: t.from.startsWith('IN') && s.time >= t.pickup ? 1 - progress(t.lifted) : 0,
    output: t.to.startsWith('OUT') ? progress(t.lifted) : 0,
  };
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
    x: positions.IN,
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
  const firstInput = s.units
    .filter((u) => u.location.startsWith('IN'))
    .sort((a, b) => a.location.localeCompare(b.location))[0];
  const candidates = s.units
    .filter(
      (u) =>
        u.until === undefined &&
        !/^(OUT|TRANS)/.test(u.location) &&
        (!u.location.startsWith('IN') || u === firstInput),
    )
    .sort((a, b) => rank(a) - rank(b) || a.ready - b.ready || a.id.localeCompare(b.id));
  for (const u of candidates) {
    let to: string | undefined;
    if (u.location === 'QA') {
      const count = s.units.filter((unit) => unit.location.startsWith('OUT')).length;
      if (count < conveyorCapacity) to = `OUT${count}`;
    } else {
      const next = u.recipe[u.step]?.machine ?? 'QA';
      if (free(s, next)) to = next;
      else if (u.location.startsWith('M')) to = ['B1', 'B2'].find((p) => free(s, p));
    }
    if (!to) continue;
    const approach = s.time + 0.3 + Math.abs(s.x - positionX(u.location)) / 0.9;
    const pickup = approach + 0.6,
      lifted = pickup + 0.6,
      fromX = positionX(u.location),
      toX = positionX(to),
      distance = Math.abs(toX - fromX),
      crossesRfid = Math.min(fromX, toX) < RFID_POSITION && RFID_POSITION < Math.max(fromX, toX),
      scanDistance = Math.abs(RFID_POSITION - fromX),
      travelDuration = 0.3 + distance / 0.9,
      scanStart = crossesRfid ? lifted + (travelDuration * scanDistance) / distance : undefined,
      scanEnd = scanStart === undefined ? undefined : scanStart + RFID_SCAN_DURATION,
      arrived = lifted + travelDuration + (crossesRfid ? RFID_SCAN_DURATION : 0);
    s.trip = {
      unit: u.id,
      from: u.location,
      to,
      start: s.time,
      approach,
      pickup,
      lifted,
      ...(scanStart === undefined ? {} : { scanStart, scanEnd }),
      arrived,
      drop: arrived + 0.6,
      end: arrived + 1.2,
      originX: s.x,
    };
    log(s, u, `Transporte ${u.location} → ${to} · destino reservado`);
    return;
  }
  if (s.units.every((u) => u.location.startsWith('OUT'))) s.status = 'complete';
  else if (!s.units.some((u) => u.until !== undefined)) s.status = 'blocked';
}
export function nextTime(s: State): number {
  const t = s.trip;
  return Math.min(
    ...s.units.flatMap((u) => (u.until === undefined ? [] : [u.until])),
    ...(t
      ? [t.approach, t.pickup, t.lifted, t.scanStart, t.scanEnd, t.arrived, t.drop, t.end].filter(
          (n): n is number => n !== undefined && n > s.time + 1e-8,
        )
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
      s.x = positionX(t.to);
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
      ? 'Esteira de saída'
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
  const from = positionX(t.from),
    to = positionX(t.to);
  let x = from,
    y = 3.4;
  if (s.time < t.approach) x = t.originX + (from - t.originX) * ease(t.start, t.approach);
  else if (s.time < t.pickup) y = 3.4 - 2 * ease(t.approach, t.pickup);
  else if (s.time < t.lifted) y = 1.4 + 2 * ease(t.pickup, t.lifted);
  else if (t.scanStart !== undefined && t.scanEnd !== undefined && s.time < t.scanStart)
    x = from + (RFID_POSITION - from) * ease(t.lifted, t.scanStart);
  else if (t.scanStart !== undefined && t.scanEnd !== undefined && s.time < t.scanEnd)
    x = RFID_POSITION;
  else if (t.scanEnd !== undefined && s.time < t.arrived)
    x = RFID_POSITION + (to - RFID_POSITION) * ease(t.scanEnd, t.arrived);
  else if (s.time < t.arrived) x = from + (to - from) * ease(t.lifted, t.arrived);
  else {
    x = to;
    y = s.time < t.drop ? 3.4 - 2 * ease(t.arrived, t.drop) : 1.4 + 2 * ease(t.drop, t.end);
  }
  return { x, y, carrying: s.time >= t.pickup && s.time < t.drop };
}
