/** Rutas oficiales del cuadro FIFA 2026 (índices 0-based en cada ronda). */

/** Dieciseisavos → octavos (índices en la lista ordenada KO-R32-1…16). */
export const R32_TO_R16 = [
  [0, 2],
  [1, 4],
  [3, 5],
  [6, 7],
  [8, 9],
  [10, 11],
  [12, 14],
  [13, 15],
];

/** Octavos → cuartos. */
export const R16_TO_QF = [
  [0, 1],
  [2, 3],
  [4, 5],
  [6, 7],
];

/**
 * Cuartos → semis (FIFA: QF1 vs QF3 y QF2 vs QF4).
 * No usar emparejamiento contiguo 0-1 / 2-3: eso produce Francia-Inglaterra en lugar de Francia-España.
 */
export const QF_TO_SF = [
  [0, 2],
  [1, 3],
];

/** Semis → final. */
export const SF_TO_FINAL = [[0, 1]];

/** Empareja ganadores según índices 0-based dentro de la ronda anterior. */
export function pairByIndices(cards, indices) {
  return indices.map(([a, b], i) => ({
    key: `proj-${i}`,
    a: cards[a]?.winner || null,
    b: cards[b]?.winner || null,
    scoreA: null,
    scoreB: null,
    winner: null,
    live: false,
    minuto: null,
    projected: true,
  }));
}

/** Octavos en adelante legacy: 1-2, 3-4, … (preferir pairByIndices con las rutas FIFA). */
export function pairSequential(cards) {
  const pairs = [];
  for (let i = 0; i < cards.length; i += 2) {
    pairs.push({
      key: `proj-${i / 2}`,
      a: cards[i]?.winner || null,
      b: cards[i + 1]?.winner || null,
      scoreA: null,
      scoreB: null,
      winner: null,
      live: false,
      minuto: null,
      projected: true,
    });
  }
  return pairs;
}

export function indicesForPhase(phaseKey) {
  switch (phaseKey) {
    case "Octavos de final":
      return R32_TO_R16;
    case "Cuartos de final":
      return R16_TO_QF;
    case "Semifinales":
      return QF_TO_SF;
    case "Final":
      return SF_TO_FINAL;
    default:
      return null;
  }
}
