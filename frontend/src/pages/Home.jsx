import { useMemo } from "react";
import Bracket from "../components/Bracket";
import KnockoutFlow from "../components/KnockoutFlow";
import LiveMatchCard from "../components/LiveMatchCard";
import StatCard from "../components/StatCard";
import { Skeleton } from "../components/Skeleton";
import { useBracket, useDashboard, useMatches, useRanking } from "../hooks/useApi";
import { formatColombia } from "../utils/dates";

const KO_PHASES = [
  "Dieciseisavos de final",
  "Octavos de final",
  "Cuartos de final",
  "Semifinales",
  "Final",
];

function scoreLine(m) {
  if (m?.goles_local != null && m?.goles_visitante != null) {
    return `${m.goles_local} - ${m.goles_visitante}`;
  }
  return null;
}

export default function Home() {
  const { data: dashboard } = useDashboard();
  const { data: bracket } = useBracket();
  const { data: liveMatches } = useMatches({ estado: "LIVE" });
  const { data: ranking } = useRanking();

  const liveMatch = liveMatches?.[0];
  const hasScore = (m) => m?.goles_local != null && m?.goles_visitante != null;
  const matchScore = (m) => (hasScore(m) ? `${m.goles_local} - ${m.goles_visitante}` : "vs");

  const knockout = bracket?.knockout || [];

  const koSummary = useMemo(() => {
    const finished = knockout.filter((m) => m.estado === "FINISHED").length;
    const live = knockout.filter((m) => m.estado === "LIVE").length;
    const scheduled = knockout.filter((m) => m.estado === "SCHEDULED").length;

    let currentPhase = "Eliminatorias";
    for (const phase of KO_PHASES) {
      const inPhase = knockout.filter((m) => m.fase === phase);
      if (inPhase.some((m) => m.estado !== "FINISHED")) {
        currentPhase = phase;
        break;
      }
    }

    const nextKo = knockout
      .filter((m) => m.estado === "SCHEDULED" && m.fecha)
      .sort((a, b) => new Date(a.fecha) - new Date(b.fecha))[0];

    return { finished, live, scheduled, total: knockout.length, currentPhase, nextKo };
  }, [knockout]);

  const topThree = (ranking || []).slice(0, 3);

  return (
    <div className="space-y-8">
      <div className="overflow-hidden rounded-3xl bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 p-6 text-white shadow-lg sm:p-8">
        <p className="text-sm font-medium uppercase tracking-widest text-brand-200">
          Copa del Mundo · USA · Canadá · México
        </p>
        <h1 className="mt-1 text-3xl font-extrabold sm:text-4xl">Mundial 2026 🏟️</h1>
        <p className="mt-2 max-w-2xl text-sm text-brand-100">
          Sigue las eliminatorias del Mundial en tiempo real: cuadro oficial, partidos en
          vivo y ranking de la quiniela.
        </p>
      </div>

      {dashboard && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title={liveMatch ? "Partido en vivo" : "Próximo partido"}
            value={
              liveMatch
                ? `${liveMatch.local} ${matchScore(liveMatch)} ${liveMatch.visitante}`
                : dashboard.proximo_partido
                ? `${dashboard.proximo_partido.local} vs ${dashboard.proximo_partido.visitante}`
                : "—"
            }
            subtitle={
              liveMatch
                ? hasScore(liveMatch)
                  ? liveMatch.minuto
                    ? `Marcador actual · ${liveMatch.minuto}`
                    : "Marcador actual"
                  : "En juego · marcador al sincronizar"
                : ""
            }
            icon={liveMatch ? "🔴" : "⏱️"}
            accent={liveMatch ? "rose" : "brand"}
          />
          <StatCard
            title="Partidos jugados"
            value={`${dashboard.partidos_jugados} / ${dashboard.total_partidos}`}
            icon="✅"
            accent="emerald"
          />
          <StatCard
            title="Líder del ranking"
            value={dashboard.lider?.nombre || "—"}
            subtitle={dashboard.lider ? `${dashboard.lider.puntos_totales} pts` : ""}
            icon="🏆"
            accent="amber"
          />
          <StatCard
            title="Participantes"
            value={dashboard.total_participantes}
            subtitle={`${dashboard.total_predicciones} predicciones`}
            icon="👥"
            accent="rose"
          />
        </div>
      )}

      {liveMatches?.length > 0 && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-xl font-bold">Partidos en vivo 🔴</h2>
            <span className="badge bg-rose-500/15 text-rose-400">
              Se actualiza automáticamente
            </span>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {liveMatches.map((m) => (
              <LiveMatchCard key={m.id} match={m} />
            ))}
          </div>
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">Camino al campeón 🏆</h2>
          <span className="badge bg-emerald-500/15 text-emerald-500">Resultados oficiales</span>
        </div>
        {bracket ? (
          <KnockoutFlow knockout={bracket.knockout || []} />
        ) : (
          <Skeleton className="h-48 w-full rounded-2xl" />
        )}
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-xl font-bold">Cuadro del Mundial 🗺️</h2>
          <div className="flex items-center gap-2">
            <span className="badge bg-emerald-500/15 text-emerald-500">
              <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
              EN VIVO
            </span>
            <span className="badge bg-brand-500/15 text-brand-400">Resultados reales</span>
          </div>
        </div>
        {bracket ? (
          <Bracket knockout={bracket.knockout || []} />
        ) : (
          <Skeleton className="h-96 w-full rounded-2xl" />
        )}
        <p className="text-xs text-slate-500 sm:hidden">
          👉 Desliza el cuadro de lado a lado para ver todas las rondas.
        </p>
        <p className="text-xs text-slate-500">
          Los cruces y ganadores se actualizan con los resultados oficiales del torneo.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-bold">Resumen del torneo</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="card space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Fase actual
            </p>
            <p className="text-lg font-bold">{koSummary.currentPhase}</p>
            {koSummary.total > 0 ? (
              <p className="text-sm text-slate-500">
                {koSummary.finished} finalizados · {koSummary.live} en vivo ·{" "}
                {koSummary.scheduled} por jugar
              </p>
            ) : (
              <p className="text-sm text-slate-500">Publica los dieciseisavos en Admin.</p>
            )}
          </div>

          <div className="card space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Último resultado
            </p>
            {dashboard?.ultimo_resultado ? (
              <>
                <p className="text-lg font-bold">
                  {dashboard.ultimo_resultado.local}{" "}
                  {scoreLine(dashboard.ultimo_resultado) || "vs"}{" "}
                  {dashboard.ultimo_resultado.visitante}
                </p>
                <p className="text-sm text-slate-500">
                  {dashboard.ultimo_resultado.fase}
                  {dashboard.ultimo_resultado.fecha &&
                    ` · ${formatColombia(dashboard.ultimo_resultado.fecha, {
                      day: "2-digit",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}`}
                </p>
              </>
            ) : (
              <p className="text-sm text-slate-500">Aún no hay resultados registrados.</p>
            )}
          </div>

          <div className="card space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Próximo partido (eliminatorias)
            </p>
            {koSummary.nextKo ? (
              <>
                <p className="text-lg font-bold">
                  {koSummary.nextKo.local} vs {koSummary.nextKo.visitante}
                </p>
                <p className="text-sm text-slate-500">
                  {koSummary.nextKo.fase}
                  {koSummary.nextKo.fecha &&
                    ` · ${formatColombia(koSummary.nextKo.fecha, {
                      day: "2-digit",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}`}
                </p>
              </>
            ) : dashboard?.proximo_partido ? (
              <>
                <p className="text-lg font-bold">
                  {dashboard.proximo_partido.local} vs {dashboard.proximo_partido.visitante}
                </p>
                <p className="text-sm text-slate-500">{dashboard.proximo_partido.fase}</p>
              </>
            ) : (
              <p className="text-sm text-slate-500">No hay partidos programados.</p>
            )}
          </div>
        </div>

        {topThree.length > 0 && (
          <div className="card">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Top 3 de la quiniela
            </p>
            <ol className="space-y-2">
              {topThree.map((r, i) => (
                <li
                  key={r.participant_id}
                  className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/60"
                >
                  <span className="flex items-center gap-2">
                    <span className="text-lg">{["🥇", "🥈", "🥉"][i]}</span>
                    <span className="font-medium">{r.nombre}</span>
                  </span>
                  <span className="font-bold tabular-nums text-brand-600 dark:text-brand-400">
                    {r.puntos_totales} pts
                  </span>
                </li>
              ))}
            </ol>
          </div>
        )}
      </section>
    </div>
  );
}
