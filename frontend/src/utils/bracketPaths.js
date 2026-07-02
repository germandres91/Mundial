/** Rutas oficiales del cuadro FIFA 2026 (KO-R32-N → octavos). */
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

/** Octavos en adelante: 1-2, 3-4, … dentro de la columna anterior. */
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
