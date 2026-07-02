function Tie({ top, bottom, highlight, scoreTop, scoreBottom, live, minuto }) {
  const showScore = scoreTop != null && scoreBottom != null;
  return (
    <div
      className={`min-w-[160px] rounded-xl border p-2.5 text-sm shadow-sm ${
        live
          ? "border-rose-500/50 ring-2 ring-rose-500/20"
          : highlight
          ? "border-amber-400/50 bg-amber-400/10"
          : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800"
      }`}
    >
      {live && (
        <p className="mb-1 text-center text-[10px] font-bold uppercase text-rose-500">
          En vivo{minuto ? ` · ${minuto}` : ""}
        </p>
      )}
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-medium">{top || "Por definir"}</span>
        {showScore && <span className="font-mono text-xs tabular-nums">{scoreTop}</span>}
      </div>
      <div className="my-1 border-t border-dashed border-slate-300 dark:border-slate-600" />
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-medium">{bottom || "Por definir"}</span>
        {showScore && <span className="font-mono text-xs tabular-nums">{scoreBottom}</span>}
      </div>
    </div>
  );
}

function Column({ title, children }) {
  return (
    <div className="flex flex-col justify-center gap-6">
      <p className="text-center text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </p>
      <div className="flex flex-col justify-center gap-6">{children}</div>
    </div>
  );
}

function byPhase(knockout) {
  const map = {};
  for (const m of knockout || []) {
    if (!m.fase) continue;
    (map[m.fase] ||= []).push(m);
  }
  for (const phase of Object.keys(map)) {
    map[phase].sort((a, b) => (a.fifa_id || "").localeCompare(b.fifa_id || ""));
  }
  return map;
}

function winnerName(m) {
  if (m.estado !== "FINISHED" || m.goles_local == null || m.goles_visitante == null) {
    return null;
  }
  if (m.ganador) return m.ganador;
  if (m.goles_local > m.goles_visitante) return m.local;
  if (m.goles_visitante > m.goles_local) return m.visitante;
  return null;
}

/**
 * Camino al campeón según resultados oficiales (actualización en vivo).
 */
export default function KnockoutFlow({ knockout = [] }) {
  const phases = byPhase(knockout);
  const semifinals = phases["Semifinales"] || [];
  const finalMatch = phases["Final"]?.[0];
  const champion = finalMatch ? winnerName(finalMatch) : null;

  if (!semifinals.length && !finalMatch) {
    const r32live = (phases["Dieciseisavos de final"] || []).filter((m) => m.estado === "LIVE");
    if (r32live.length) {
      const m = r32live[0];
      return (
        <div className="card overflow-x-auto">
          <div className="flex min-w-max items-stretch gap-8 p-2">
            <Column title="Dieciseisavos en juego">
              <Tie
                top={m.local}
                bottom={m.visitante}
                scoreTop={m.goles_local}
                scoreBottom={m.goles_visitante}
                live
                minuto={m.minuto}
              />
            </Column>
          </div>
        </div>
      );
    }
    return (
      <div className="card text-center text-sm text-slate-500">
        El camino al campeón se irá completando a medida que avancen las eliminatorias.
      </div>
    );
  }

  const sf1 = semifinals[0];
  const sf2 = semifinals[1];

  return (
    <div className="card overflow-x-auto">
      <div className="flex min-w-max items-stretch gap-8 p-2">
        {semifinals.length > 0 && (
          <Column title="Semifinales">
            {sf1 && (
              <Tie
                top={sf1.local}
                bottom={sf1.visitante}
                scoreTop={sf1.goles_local}
                scoreBottom={sf1.goles_visitante}
                live={sf1.estado === "LIVE"}
                minuto={sf1.minuto}
              />
            )}
            {sf2 && (
              <Tie
                top={sf2.local}
                bottom={sf2.visitante}
                scoreTop={sf2.goles_local}
                scoreBottom={sf2.goles_visitante}
                live={sf2.estado === "LIVE"}
                minuto={sf2.minuto}
              />
            )}
          </Column>
        )}

        {finalMatch && (
          <Column title="Final">
            <Tie
              top={finalMatch.local}
              bottom={finalMatch.visitante}
              scoreTop={finalMatch.goles_local}
              scoreBottom={finalMatch.goles_visitante}
              live={finalMatch.estado === "LIVE"}
              minuto={finalMatch.minuto}
              highlight
            />
          </Column>
        )}

        <Column title="Campeón">
          <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-amber-400/60 bg-gradient-to-b from-amber-400/20 to-amber-500/5 px-6 py-5 text-center">
            <span className="text-4xl">🏆</span>
            <span className="text-lg font-extrabold">{champion || "Por definir"}</span>
            <span className="text-xs text-slate-500">Campeón del Mundo</span>
          </div>
        </Column>
      </div>
    </div>
  );
}
