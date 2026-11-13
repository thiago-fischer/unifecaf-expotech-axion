export type Unit = {
  id: string;
  product: string;
  location: string;
  rejected?: boolean;
  reviewed?: boolean;
};
type Pose = { x: number; y: number; carrying: boolean };
export type State = {
  time: number;
  units: Unit[];
  live: {
    session: string;
    pose: Pose;
    poseAt: (now: number) => Pose;
    movingUntil: number;
    rfid: string | null;
    machines: Record<string, { estado: string; tempo_restante_ms: number | null }>;
  };
};
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

export function initialScene(): State {
  const pose = { x: positions.IN, y: 3.4, carrying: false };
  return {
    time: 0,
    units: [],
    live: { session: '', pose, poseAt: () => pose, movingUntil: 0, rfid: null, machines: {} },
  };
}
