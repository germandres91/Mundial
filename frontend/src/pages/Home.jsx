import Bracket from "../components/Bracket";
import GroupCard from "../components/GroupCard";
import KnockoutFlow from "../components/KnockoutFlow";
import LiveMatchCard from "../components/LiveMatchCard";
import StatCard from "../components/StatCard";
import { Skeleton } from "../components/Skeleton";
import { useBracket, useDashboard, useMatches } from "../hooks/useApi";

export default function Home() {
  const { data: dashboard } = useDashboard();
  const { data: bracket, isLoading } = useBracket();
  const { data: liveMatches } = useMatches({ estado: "LIVE" });

  const liveMatch = liveMatches?.[0];
  const hasScore = (m) => m?.goles_local != null && m?.goles_visitante != null;
  const matchScore = (m) => (hasScore(m) ? `${m.goles_local} - ${m.goles_visitante}` : "vs");

  return (
    <div className="space-y-8">
      <div className="overflow-hidden rounded-3xl bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 p-6 text-white shadow-lg sm:p-8">
        <p className="text-sm font-medium uppercase tracking-widest text-brand-200">
          Copa del Mundo · USA · Canadá · México
        </p>
        <h1 className="mt-1 text-3xl font-extrabold sm:text-4xl">Mundial 2026 🏟️</h1>
        <p className="mt-2 max-w-2xl text-sm text-brand-100">
          Sigue el avance del torneo en tiempo real: fase de grupos y eliminatorias se
          actualizan con los resultados oficiales para todos.
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
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">Fase de grupos</h2>
          <span className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Clasifican (top 2)
          </span>
        </div>
        {isLoading ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-40 w-full rounded-2xl" />
            ))}
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {(bracket?.grupos || []).map((g) => (
              <GroupCard key={g.grupo} grupo={g.grupo} rows={g.posiciones || []} />
            ))}
          </div>
        )}
        <p className="text-xs text-slate-500">
          Posiciones según los resultados oficiales registrados en el torneo.
        </p>
      </section>
    </div>
  );
}
