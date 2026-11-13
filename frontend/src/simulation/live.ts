import { positions, RFID_POSITION, type State, type Unit } from './engine';

export type LiveStatus = {
  sessao_id: string;
  velocidade: number;
  idade_ms?: number;
  mesa: {
    posicao: string | null;
    movimento: {
      origem: string | null;
      destino: string;
      progresso: number;
      duracao_ms?: number;
      manipulacao_ms?: number;
    } | null;
    progresso_cabecote: number;
    manipulacao_ms?: number;
  };
  pecas: Record<string, string>;
  rfid_transportado: string | null;
  resultados_qa: Record<string, 'aprovada' | 'rejeitada'>;
  leitura_rfid: string | null;
  maquinas: NonNullable<State['live']>['machines'];
  falhas: { mensagem?: string }[];
  execution: {
    id: string;
    order_id: number;
    state: 'queued' | 'running' | 'completed' | 'interrupted';
    unit_rfids: Record<string, string>;
    completed_operations: string[];
    approved_units: string[];
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
  const elapsed = (snapshot.idade_ms ?? 0) * snapshot.velocidade;
  const travel = move?.duracao_ms ?? 0;
  const handling = (move ? move.manipulacao_ms : snapshot.mesa.manipulacao_ms) ?? 0;
  const receivedAt = performance.now();
  const travelLeft = move ? travel * (1 - move.progresso) : 0;
  const handlingLeft = handling * (1 - snapshot.mesa.progresso_cabecote);
  const movingUntil =
    receivedAt + Math.max(0, travelLeft + handlingLeft - elapsed) / snapshot.velocidade;
  function poseAt(now: number) {
    const age = elapsed + Math.max(0, now - receivedAt) * snapshot.velocidade;
    const progress = move ? Math.min(1, move.progresso + (travel ? age / travel : 0)) : 0;
    const x = move
      ? axis(move.origem) + (axis(move.destino) - axis(move.origem)) * progress
      : axis(snapshot.mesa.posicao);
    const head = Math.min(
      1,
      snapshot.mesa.progresso_cabecote + (handling ? Math.max(0, age - travelLeft) / handling : 0),
    );
    const depth = 1 - Math.abs(2 * head - 1);
    const y = 3.4 - 2 * depth * depth * (3 - 2 * depth);
    return { x, y, carrying: snapshot.rfid_transportado !== null };
  }
  const pose = poseAt(receivedAt);
  return {
    time: receivedAt / 1000,
    units,
    x: pose.x,
    events: [],
    status:
      snapshot.execution?.state === 'completed'
        ? 'complete'
        : snapshot.execution?.state === 'interrupted'
          ? 'blocked'
          : 'active',
    live: {
      session: snapshot.sessao_id,
      pose,
      poseAt,
      movingUntil,
      rfid: snapshot.leitura_rfid,
      machines: Object.fromEntries(
        Object.entries(snapshot.maquinas).map(([name, machine]) => [
          name,
          {
            ...machine,
            tempo_restante_ms:
              machine.tempo_restante_ms === null
                ? null
                : Math.max(0, machine.tempo_restante_ms - elapsed),
          },
        ]),
      ),
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
