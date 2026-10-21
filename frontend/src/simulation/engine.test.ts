import { describe, it, expect } from 'vitest';
import { advance, createState, nextEvent, type State } from './engine';
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
});
