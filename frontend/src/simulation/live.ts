import { positions, RFID_POSITION, type State, type Unit } from './engine';

export type LiveStatus = {
  sessao_id: string;
  mesa: {
    posicao: string | null;
    movimento: { origem: string | null; destino: string; progresso: number } | null;
    progresso_cabecote: number;
  };
  pecas: Record<string, string>;
  rfid_transportado: string | null;
  resultados_qa: Record<string, 'aprovada' | 'rejeitada'>;
  leitura_rfid: string | null;
  maquinas: NonNullable<State['live']>['machines'];
  falhas: { mensagem?: string }[];
  execution: {
    order_id: number;
    state: 'queued' | 'running' | 'completed' | 'interrupted';
    unit_rfids: Record<string, string>;
    rejected_units: Record<string, string>;
    reason: string | null;
  } | null;
};

function axis(slot: string | null) {
  if (slot?.startsWith('ARMAZEM') || slot === 'REFERENCIA') return positions.IN;
  if (slot?.startsWith('ESTOQUE_FINAL')) return positions.OUT;
  if (slot === 'LEITOR_RFID') return RFID_POSITION;
  return (slot && positions[slot]) || positions.IN;
}

export function liveState(snapshot: LiveStatus): State {
  const unitNames = new Map(
    Object.entries(snapshot.execution?.unit_rfids ?? {}).map(([unit, rfid]) => [rfid, unit]),
  );
  const pieces = Object.entries(snapshot.pecas).sort(([a], [b]) => a.localeCompare(b));
  let outputIndex = 0;
  const units: Unit[] = pieces.map(([slot, rfid]) => ({
    ...liveUnit(rfid),
    location: slot.startsWith('ARMAZEM_')
      ? `IN${slot.slice(-2)}`
      : slot.startsWith('ESTOQUE_FINAL_')
        ? `OUT${outputIndex++}`
        : slot,
  }));
  if (snapshot.rfid_transportado) {
    units.push({ ...liveUnit(snapshot.rfid_transportado), location: 'TRANS' });
  }
  const move = snapshot.mesa.movimento;
  const x = move
    ? axis(move.origem) + (axis(move.destino) - axis(move.origem)) * move.progresso
    : axis(snapshot.mesa.posicao);
  const y = 3.4 - 2 * (1 - Math.abs(2 * snapshot.mesa.progresso_cabecote - 1));
  return {
    time: performance.now() / 1000,
    units,
    x,
    events: [],
    status:
      snapshot.execution?.state === 'completed'
        ? 'complete'
        : snapshot.execution?.state === 'interrupted'
          ? 'blocked'
          : 'active',
    live: {
      session: snapshot.sessao_id,
      pose: { x, y, carrying: snapshot.rfid_transportado !== null },
      rfid: snapshot.leitura_rfid,
      machines: snapshot.maquinas,
    },
  };

  function liveUnit(rfid: string): Omit<Unit, 'location'> {
    const quality = snapshot.resultados_qa[rfid];
    return {
      id: rfid,
      product: unitNames.get(rfid) ?? '',
      expectedProduct: '',
      recipe: [],
      step: 0,
      ready: 0,
      history: [],
      completed: [],
      reviewed: quality !== undefined,
      rejected: quality === 'rejeitada',
    };
  }
}
