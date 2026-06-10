// Definiciones de tipos (JSDoc) para autocompletado y documentación.

/**
 * @typedef {Object} Match
 * @property {number} id
 * @property {string|null} fifa_id
 * @property {string|null} grupo
 * @property {string|null} fase
 * @property {string} local
 * @property {string} visitante
 * @property {string|null} fecha
 * @property {number|null} goles_local
 * @property {number|null} goles_visitante
 * @property {"SCHEDULED"|"LIVE"|"FINISHED"|"POSTPONED"|"CANCELLED"} estado
 */

/**
 * @typedef {Object} RankingRow
 * @property {number} participant_id
 * @property {string} nombre
 * @property {number} puntos_totales
 * @property {number} posicion
 * @property {number} aciertos_exactos
 * @property {number} partidos_acertados
 */

/**
 * @typedef {Object} DashboardSummary
 * @property {Match|null} proximo_partido
 * @property {Match|null} ultimo_resultado
 * @property {RankingRow|null} lider
 * @property {number} partidos_jugados
 * @property {number} partidos_pendientes
 * @property {number} total_partidos
 * @property {number} total_participantes
 * @property {number} total_predicciones
 */

export const MATCH_STATUS_LABELS = {
  SCHEDULED: "Programado",
  LIVE: "En vivo",
  FINISHED: "Finalizado",
  POSTPONED: "Aplazado",
  CANCELLED: "Cancelado",
};
