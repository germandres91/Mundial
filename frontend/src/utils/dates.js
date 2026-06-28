/** Parsea ISO asumiendo UTC cuando no trae zona horaria (SQLite / API legacy). */
export function parseUtc(iso) {
  if (!iso) return null;
  if (iso.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(iso)) {
    return new Date(iso);
  }
  return new Date(`${iso}Z`);
}

export function formatColombia(iso, options = {}) {
  const d = parseUtc(iso);
  if (!d || Number.isNaN(d.getTime())) return "Por definir";
  return d.toLocaleString("es-CO", {
    timeZone: "America/Bogota",
    ...options,
  });
}

/** Etiqueta desde metadata oficial (fecha calendario COL + hora). */
export function formatMatchSchedule(match) {
  if (match?.fecha_dia_colombia && match?.hora_colombia) {
    const [y, m, day] = match.fecha_dia_colombia.split("-").map(Number);
    const d = new Date(y, m - 1, day);
    const dayLabel = d.toLocaleDateString("es-CO", {
      day: "2-digit",
      month: "short",
    });
    return `${dayLabel}, ${match.hora_colombia} (hora COL)`;
  }
  return formatColombia(match?.fecha, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
