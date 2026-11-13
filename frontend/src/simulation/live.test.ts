import { expect, it } from 'vitest';
import { positions, RFID_POSITION } from './engine';
import { liveState, type LiveStatus } from './live';

it('usa posições, RFIDs e resultados informados pelo controlador', () => {
  const snapshot: LiveStatus = {
    sessao_id: 'sim',
    mesa: {
      posicao: 'ARMAZEM',
      movimento: { origem: 'ARMAZEM', destino: 'LEITOR_RFID', progresso: 0.5 },
      progresso_cabecote: 0,
    },
    pecas: { ARMAZEM_03: 'SIM-003', B2: 'SIM-002', ESTOQUE_FINAL_01: 'SIM-001' },
    rfid_transportado: 'SIM-004',
    resultados_qa: { 'SIM-001': 'rejeitada' },
    leitura_rfid: null,
    maquinas: {},
    falhas: [],
    execution: {
      order_id: 1,
      state: 'running',
      unit_rfids: { 'p1-u1': 'SIM-001' },
      rejected_units: { 'p1-u1': 'RFID divergente' },
      reason: null,
    },
  };
  const state = liveState(snapshot);
  expect(state.live?.pose).toEqual({
    x: (positions.IN + RFID_POSITION) / 2,
    y: 3.4,
    carrying: true,
  });
  expect(state.units).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ id: 'SIM-003', location: 'IN03' }),
      expect.objectContaining({ id: 'SIM-002', location: 'B2' }),
      expect.objectContaining({
        id: 'SIM-001',
        product: 'p1-u1',
        location: 'OUT0',
        rejected: true,
        reviewed: true,
      }),
      expect.objectContaining({ id: 'SIM-004', location: 'TRANS' }),
    ]),
  );
});
