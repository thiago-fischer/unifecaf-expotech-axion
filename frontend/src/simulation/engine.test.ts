import { describe, it, expect } from 'vitest';
import {
  advance,
  createState,
  nextEvent,
  pose,
  RFID_POSITION,
  RFID_SCAN_DURATION,
  type State,
} from './engine';
function finish(s: State) {
  for (let i = 0; i < 2000 && s.status !== 'complete' && s.status !== 'blocked'; i++) nextEvent(s);
  return s;
}
describe('simulação determinística', () => {
  it('conclui seis unidades com estoque auxiliar e paralelismo, sem duplicar locais', () => {
    const s = createState();
    let parallel = false;
    for (let i = 0; i < 2000 && s.status !== 'complete' && s.status !== 'blocked'; i++) {
      nextEvent(s);
      const loc = s.units.map((u) => u.location);
      expect(new Set(loc).size).toBe(loc.length);
      parallel ||=
        s.units.filter((u) => u.until !== undefined && u.location.startsWith('M')).length > 1;
    }
    expect(s.status).toBe('complete');
    expect(s.units.every((u) => u.location.startsWith('OUT'))).toBe(true);
    expect(s.events.some((e) => e.text === 'Entregue em B1')).toBe(true);
    expect(parallel).toBe(true);
  });
  it('independe da frequência de atualização', () => {
    const a = finish(createState()),
      b = createState();
    for (let i = 0; i < 100000 && b.status !== 'complete' && b.status !== 'blocked'; i++)
      advance(b, 0.13);
    expect(b.events).toEqual(a.events);
    expect(b.time).toBe(a.time);
  });
  it('rejeita histórico inconsistente', () => {
    const s = createState();
    s.units[0].completed.push('M9');
    s.units[1].product = 'C';
    finish(s);
    expect(s.units[0].location).toBe('REJ0');
    expect(s.units[1].location).toBe('REJ1');
    expect(s.units[0].history.some((h) => h.includes('inconsistente'))).toBe(true);
  });
  it('detecta bloqueio quando máquinas e buffers estão cheios', () => {
    const s = createState();
    ['M1', 'M2', 'M3', 'B1', 'B2', 'IN5'].forEach((p, i) => {
      s.units[i].location = p;
      s.units[i].recipe = [{ machine: i === 0 ? 'M2' : 'M1', seconds: 2 }];
    });
    advance(s, 0);
    expect(s.status).toBe('blocked');
  });
  it('suporta etapas consecutivas e revisita', () => {
    const s = createState();
    s.units = s.units.slice(0, 1);
    s.units[0].recipe = [
      { machine: 'M1', seconds: 1 },
      { machine: 'M1', seconds: 2 },
      { machine: 'M2', seconds: 1 },
      { machine: 'M1', seconds: 1 },
    ];
    finish(s);
    expect(s.units[0].completed).toEqual(['M1', 'M1', 'M2', 'M1']);
    expect(s.status).toBe('complete');
  });
  it('reserva destino e só libera origem depois de coletar', () => {
    const s = createState();
    advance(s, 0);
    const t = s.trip!;
    expect(t.to).toBe('M1');
    expect(s.units[0].location).toBe('IN0');
    advance(s, t.pickup);
    expect(s.units[0].location).toBe('TRANS');
    expect(s.trip?.to).toBe('M1');
  });
  it('para diante do leitor RFID por 0,01 segundo simulado', () => {
    const s = createState();
    advance(s, 0);
    const trip = s.trip!;
    expect(trip.scanStart).toBeDefined();
    expect(trip.scanEnd! - trip.scanStart!).toBeCloseTo(RFID_SCAN_DURATION, 10);

    advance(s, trip.scanStart! - s.time);
    expect(pose(s).x).toBeCloseTo(RFID_POSITION, 10);

    const stoppedAt = s.time;
    advance(s, RFID_SCAN_DURATION / 2);
    expect(pose(s).x).toBeCloseTo(RFID_POSITION, 10);
    advance(s, RFID_SCAN_DURATION / 2);
    expect(s.time - stoppedAt).toBeCloseTo(RFID_SCAN_DURATION, 10);
    expect(pose(s).x).toBeCloseTo(RFID_POSITION, 10);

    advance(s, 0.001);
    expect(pose(s).x).toBeGreaterThan(RFID_POSITION);
  });
  it('desce para entregar a unidade na baia depois de passar pelo leitor', () => {
    const s = createState();
    advance(s, 0);
    const trip = s.trip!;

    advance(s, trip.arrived - s.time);
    expect(pose(s).x).toBeCloseTo(-4, 10);
    expect(pose(s).y).toBeCloseTo(3.4, 10);

    advance(s, (trip.drop - trip.arrived) / 2);
    expect(pose(s).y).toBeCloseTo(2.4, 10);

    advance(s, trip.drop - s.time);
    expect(pose(s).y).toBeCloseTo(1.4, 10);
  });
  it('não adiciona parada RFID aos trajetos que não cruzam o leitor', () => {
    const s = createState();
    s.units = s.units.slice(0, 1);
    s.units[0].location = 'M1';
    s.units[0].step = 1;
    s.units[0].recipe = [
      { machine: 'M1', seconds: 1 },
      { machine: 'M2', seconds: 1 },
    ];
    advance(s, 0);
    expect(s.trip?.to).toBe('M2');
    expect(s.trip?.scanStart).toBeUndefined();
    expect(s.trip?.scanEnd).toBeUndefined();
  });
});
