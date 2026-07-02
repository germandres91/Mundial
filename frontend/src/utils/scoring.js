/** Marcador válido para puntuar predicciones (solo 90 minutos reglamentarios). */
export function scoringGoals(match) {
  if (!match) return null;
  if (match.goles_local_90 != null && match.goles_visitante_90 != null) {
    return { local: match.goles_local_90, visitante: match.goles_visitante_90 };
  }
  if (match.goles_local != null && match.goles_visitante != null) {
    return { local: match.goles_local, visitante: match.goles_visitante };
  }
  return null;
}

/** Evalúa visualmente la predicción: exacto, parcial (acierto) o fallo. */
export function evaluatePrediction(predLocal, predVisitante, match) {
  const real = scoringGoals(match);
  if (!real) return null;
  if (predLocal === real.local && predVisitante === real.visitante) return "exacto";
  const predSign = Math.sign(predLocal - predVisitante);
  const realSign = Math.sign(real.local - real.visitante);
  if (predSign === realSign) return "parcial";
  return "fallo";
}
