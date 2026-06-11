import { flagUrl } from "../utils/flags";

function Flag({ name }) {
  const url = flagUrl(name);
  if (!url) return null;
  return (
    <img
      src={url}
      alt=""
      loading="lazy"
      className="h-4 w-6 shrink-0 rounded-sm object-cover ring-1 ring-black/10"
      onError={(e) => {
        e.currentTarget.style.visibility = "hidden";
      }}
    />
  );
}

function formatDate(iso) {
  if (!iso) return "Por definir";
  return new Date(iso).toLocaleString("es-CO", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Bogota",
  });
}

/**
 * Tarjeta de partido en vivo con marcador actual y, si se entrega, el
 * pronóstico del participante seleccionado para ese partido.
 */
export default function LiveMatchCard({ match, prediction, participantName }) {
  const hasScore = match.goles_local != null && match.goles_visitante != null;

  return (
    <div className="card animate-fade-in ring-1 ring-rose-500/40">
      <div className="mb-3 flex items-center justify-between text-xs text-slate-500">
        <span>
          {match.fase || "—"} {match.grupo ? `· Grupo ${match.grupo}` : ""}
        </span>
        <span className="badge animate-pulse bg-rose-500/15 text-rose-400">
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-rose-500" />
          EN VIVO{match.minuto ? ` · ${match.minuto}` : ""}
        </span>
      </div>

      {/* Marcador actual */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex flex-1 items-center justify-end gap-2 truncate">
          <span className="truncate font-semibold">{match.local}</span>
          <Flag name={match.local} />
        </div>
        <span className="rounded-lg bg-rose-500/15 px-3 py-1 text-xl font-extrabold tabular-nums text-rose-500">
          {hasScore ? `${match.goles_local} - ${match.goles_visitante}` : "vs"}
        </span>
        <div className="flex flex-1 items-center gap-2 truncate">
          <Flag name={match.visitante} />
          <span className="truncate font-semibold">{match.visitante}</span>
        </div>
      </div>

      {/* Pronóstico del participante */}
      <div className="mt-3 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
          Pronóstico{participantName ? ` · ${participantName}` : ""}
        </p>
        {prediction ? (
          <p className="text-sm font-bold tabular-nums">
            {match.local} {prediction.pred_local} - {prediction.pred_visitante}{" "}
            {match.visitante}
          </p>
        ) : (
          <p className="text-sm text-slate-500">Sin pronóstico para este partido.</p>
        )}
      </div>

      <div className="mt-3 flex items-center gap-1.5 text-xs text-slate-500">
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-rose-500" />
        En juego · {formatDate(match.fecha)} (hora COL)
      </div>
    </div>
  );
}
