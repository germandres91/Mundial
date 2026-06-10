import { useState } from "react";
import MatchCard from "../components/MatchCard";
import { SkeletonCard } from "../components/Skeleton";
import { useMatches } from "../hooks/useApi";
import { MATCH_STATUS_LABELS } from "../types";

const FILTERS = ["TODOS", "SCHEDULED", "LIVE", "FINISHED"];

export default function Matches() {
  const [filter, setFilter] = useState("TODOS");
  const params = filter === "TODOS" ? undefined : { estado: filter };
  const { data: matches, isLoading } = useMatches(params);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold">Partidos</h1>
          <p className="text-sm text-slate-500">Calendario y resultados del Mundial.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-xl px-3 py-1.5 text-sm font-medium transition ${
                filter === f
                  ? "bg-brand-600 text-white"
                  : "bg-slate-200 text-slate-600 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              }`}
            >
              {f === "TODOS" ? "Todos" : MATCH_STATUS_LABELS[f]}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : matches?.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {matches.map((m) => (
            <MatchCard key={m.id} match={m} />
          ))}
        </div>
      ) : (
        <div className="card text-center text-slate-500">No hay partidos para mostrar.</div>
      )}
    </div>
  );
}
