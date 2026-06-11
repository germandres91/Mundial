import { useEffect, useState } from "react";
import Bracket from "../components/Bracket";
import GroupCard from "../components/GroupCard";
import KnockoutFlow from "../components/KnockoutFlow";
import MatchCard from "../components/MatchCard";
import StatCard from "../components/StatCard";
import { Skeleton } from "../components/Skeleton";
import { useBracket, useDashboard, useMatches, useParticipants } from "../hooks/useApi";

export default function Home() {
  const { data: participants } = useParticipants();
  const [participantId, setParticipantId] = useState(null);
  const { data: dashboard } = useDashboard();
  const { data: bracket, isLoading } = useBracket(participantId);
  const { data: liveMatches } = useMatches({ estado: "LIVE" });

  // Selecciona automáticamente el primer participante
  useEffect(() => {
    if (participantId == null && participants?.length) {
      setParticipantId(participants[0].id);
    }
  }, [participants, participantId]);

  const selected = participants?.find((p) => p.id === participantId);
  const liveMatch = liveMatches?.[0];

  const standingsOf = (g) => g.pronostico || g.posiciones;
  const hasScore = (m) => m?.goles_local != null && m?.goles_visitante != null;
  const matchScore = (m) => (hasScore(m) ? `${m.goles_local} - ${m.goles_visitante}` : "vs");

  return (
    <div className="space-y-8">
      {/* Encabezado */}
      <div className="overflow-hidden rounded-3xl bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 p-6 text-white shadow-lg sm:p-8">
        <p className="text-sm font-medium uppercase tracking-widest text-brand-200">
          Copa del Mundo · USA · Canadá · México
        </p>
        <h1 className="mt-1 text-3xl font-extrabold sm:text-4xl">Mundial 2026 🏟️</h1>
        <p className="mt-2 max-w-2xl text-sm text-brand-100">
          Sigue el camino al título: fase de grupos y eliminatorias se llenan a
          medida que avanza el torneo y según tus pronósticos.
        </p>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <label className="text-sm text-brand-100">Ver pronóstico de:</label>
          <select
            className="rounded-xl border-0 bg-white/15 px-3 py-2 text-sm font-medium text-white backdrop-blur focus:outline-none focus:ring-2 focus:ring-white/50 [&>option]:text-slate-900"
            value={participantId ?? ""}
            onChange={(e) => setParticipantId(Number(e.target.value))}
          >
            {(participants || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Resumen */}
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
                  ? "Marcador actual"
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
              <MatchCard key={m.id} match={m} />
            ))}
          </div>
        </section>
      )}

      {/* Camino al campeón */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">Camino al campeón 🏆</h2>
          {selected && (
            <span className="badge bg-brand-500/15 text-brand-400">
              Pronóstico de {selected.nombre}
            </span>
          )}
        </div>
        {bracket ? (
          <KnockoutFlow top4={bracket.top4 || []} />
        ) : (
          <Skeleton className="h-48 w-full rounded-2xl" />
        )}
      </section>

      {/* Bracket del Mundial */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-xl font-bold">Cuadro del Mundial 🗺️</h2>
          <div className="flex items-center gap-2">
            <span className="badge bg-emerald-500/15 text-emerald-500">
              <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
              EN VIVO
            </span>
            <span className="badge bg-brand-500/15 text-brand-400">
              {bracket?.fuente === "pronostico" ? "Proyección por pronóstico" : "Resultados reales"}
            </span>
          </div>
        </div>
        {bracket ? (
          <Bracket qualified={bracket.qualified || []} knockout={bracket.knockout || []} />
        ) : (
          <Skeleton className="h-96 w-full rounded-2xl" />
        )}
        <p className="text-xs text-slate-500 sm:hidden">
          👉 Desliza el cuadro de lado a lado para ver todas las rondas.
        </p>
        <p className="text-xs text-slate-500">
          Clasificados (12 primeros + 12 segundos + 8 mejores terceros) sembrados
          en el cuadro de eliminatorias. Los cruces de cada ronda se completan
          automáticamente con los resultados oficiales del torneo.
        </p>
      </section>

      {/* Fase de grupos */}
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
              <GroupCard key={g.grupo} grupo={g.grupo} rows={standingsOf(g)} />
            ))}
          </div>
        )}
        <p className="text-xs text-slate-500">
          Posiciones según el pronóstico seleccionado. Cuando se registren
          resultados reales, las tablas se actualizarán automáticamente.
        </p>
      </section>
    </div>
  );
}
