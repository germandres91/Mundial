import { useMemo, useState } from "react";
import Bracket from "../components/Bracket";
import KnockoutFlow from "../components/KnockoutFlow";
import LiveMatchCard from "../components/LiveMatchCard";
import StatCard from "../components/StatCard";
import { Skeleton } from "../components/Skeleton";
import {
  useBracket,
  useDashboard,
  useMatches,
  useParticipants,
  usePredictions,
  useRanking,
} from "../hooks/useApi";
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
  const { data: participants } = useParticipants();
  const [participantId, setParticipantId] = useState("");

  const selectedParticipant = (participants || []).find(
    (p) => String(p.id) === participantId
  );

  const { data: predictions } = usePredictions({
    participant_id: participantId ? Number(participantId) : null,
  });

  const predictionByMatchId = useMemo(() => {
    const map = new Map();
    for (const p of predictions || []) {
      const mid = p.match_id ?? p.match?.id;
      if (mid != null) map.set(mid, p);
    }
    return map;
  }, [predictions]);

  const trackedLiveMatches = useMemo(() => {
    const fromApi = liveMatches || [];
    if (fromApi.length) return fromApi;
    return knockout.filter((m) => m.estado === "LIVE");
  }, [liveMatches, knockout]);

  const liveMatch = trackedLiveMatches[0];
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

      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold">
              {trackedLiveMatches.length > 0 ? "Partidos en vivo 🔴" : "Pronósticos en partidos"}
            </h2>
            <p className="mt-0.5 text-sm text-slate-500">
              Elige un participante para ver su pronóstico en los partidos en juego.
            </p>
          </div>
          <div className="flex min-w-[220px] flex-1 flex-col gap-1 sm:max-w-xs">
            <label className="text-xs font-medium text-slate-500">Ver pronóstico de</label>
            <select
              className="input py-2 text-sm"
              value={participantId}
              onChange={(e) => setParticipantId(e.target.value)}
            >
              <option value="">Selecciona un participante…</option>
              {(participants || []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre}
                </option>
              ))}
            </select>
          </div>
          {trackedLiveMatches.length > 0 && (
            <span className="badge bg-rose-500/15 text-rose-400">
              Se actualiza automáticamente
            </span>
          )}
        </div>

        {trackedLiveMatches.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {trackedLiveMatches.map((m) => (
              <LiveMatchCard
                key={m.id}
                match={m}
                prediction={predictionByMatchId.get(m.id)}
                participantName={selectedParticipant?.nombre}
              />
            ))}
          </div>
        ) : (
          <div className="card text-sm text-slate-500">
            {participantId
              ? "No hay partidos en vivo ahora. Cuando empiece uno, verás aquí el marcador y el pronóstico del participante seleccionado."
              : "No hay partidos en vivo. Selecciona un participante arriba para consultar sus pronósticos cuando haya partidos en juego."}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-xl font-bold">Cuadro del Mundial 🗺️</h2>
          <div className="flex flex-wrap items-center gap-2">
            {koSummary.live > 0 && (
              <span className="badge bg-rose-500/15 text-rose-400">
                <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-rose-500" />
                {koSummary.live} en vivo
              </span>
            )}
            <span className="badge bg-emerald-500/15 text-emerald-500">Resultados oficiales</span>
          </div>
        </div>
        {bracket ? (
          <Bracket knockout={knockout} />
        ) : (
          <Skeleton className="h-96 w-full rounded-2xl" />
        )}
        <p className="text-xs text-slate-500">
          Cuadro clásico de eliminatorias: desliza con el dedo en cualquier dirección para
          explorarlo. Se actualiza en vivo con los goles.
        </p>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">Camino al campeón 🏆</h2>
          <span className="badge bg-emerald-500/15 text-emerald-500">Resultados oficiales</span>
        </div>
        {bracket ? (
          <KnockoutFlow knockout={knockout} />
        ) : (
          <Skeleton className="h-48 w-full rounded-2xl" />
        )}
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
