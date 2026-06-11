import StatusBadge from "./StatusBadge";

function formatDate(iso) {
  if (!iso) return "Por definir";
  return (
    new Date(iso).toLocaleString("es-CO", {
      weekday: "short",
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "America/Bogota",
    }) + " (hora COL)"
  );
}

export default function MatchCard({ match, onAction, actionLabel }) {
  const finished = match.estado === "FINISHED";
  const live = match.estado === "LIVE";
  const hasScore = match.goles_local != null && match.goles_visitante != null;
  const showScore = (finished || live) && hasScore;

  return (
    <div
      className={`card animate-fade-in ${
        live ? "ring-1 ring-rose-500/40" : ""
      }`}
    >
      <div className="mb-3 flex items-center justify-between text-xs text-slate-500">
        <span>{match.fase || "—"} {match.grupo ? `· Grupo ${match.grupo}` : ""}</span>
        <StatusBadge status={match.estado} />
      </div>
      <div className="flex items-center justify-between gap-3">
        <span className="flex-1 truncate text-right font-semibold">{match.local}</span>
        <span
          className={`rounded-lg px-3 py-1 text-lg font-bold ${
            live
              ? "bg-rose-500/15 text-rose-500"
              : "bg-slate-100 dark:bg-slate-800"
          }`}
        >
          {showScore ? `${match.goles_local} - ${match.goles_visitante}` : "vs"}
        </span>
        <span className="flex-1 truncate font-semibold">{match.visitante}</span>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-xs text-slate-500">
          {live && (
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-rose-500" />
          )}
          {live ? (match.minuto ? `En juego ${match.minuto} · ` : "En juego · ") : ""}
          {formatDate(match.fecha)}
        </span>
        {onAction && (
          <button className="btn-ghost px-3 py-1 text-xs" onClick={() => onAction(match)}>
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  );
}
