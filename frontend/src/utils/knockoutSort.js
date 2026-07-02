/** Orden numérico de partidos KO-R32-1 … KO-R32-16 (no alfabético). */
const KO_SLOT = /^KO-(R32|R16|QF|SF|F)-(\d+)$/;

const ROUND_RANK = { R32: 0, R16: 1, QF: 2, SF: 3, F: 4 };

export function knockoutSlotKey(fifaId) {
  if (!fifaId) return [99, 9999, ""];
  const m = fifaId.match(KO_SLOT);
  if (!m) return [99, 9999, fifaId];
  return [ROUND_RANK[m[1]] ?? 98, parseInt(m[2], 10), fifaId];
}

export function compareKnockoutFifaId(a, b) {
  const ka = knockoutSlotKey(a);
  const kb = knockoutSlotKey(b);
  for (let i = 0; i < 3; i += 1) {
    if (ka[i] < kb[i]) return -1;
    if (ka[i] > kb[i]) return 1;
  }
  return 0;
}

export function sortKnockoutMatches(matches) {
  return [...(matches || [])].sort((a, b) =>
    compareKnockoutFifaId(a.fifa_id, b.fifa_id)
  );
}

const PHASE_RANK = {
  "Dieciseisavos de final": 1,
  "Octavos de final": 2,
  "Cuartos de final": 3,
  Semifinales: 4,
  Final: 5,
};

export function sortMatchesForTable(matches) {
  return [...(matches || [])].sort((a, b) => {
    const pa = PHASE_RANK[a.fase] ?? (a.fase === "Fase de grupos" ? 0 : 50);
    const pb = PHASE_RANK[b.fase] ?? (b.fase === "Fase de grupos" ? 0 : 50);
    if (pa !== pb) return pa - pb;
    if (pa > 0) return compareKnockoutFifaId(a.fifa_id, b.fifa_id);
    const da = a.fecha ? new Date(a.fecha).getTime() : 0;
    const db = b.fecha ? new Date(b.fecha).getTime() : 0;
    return da - db;
  });
}
