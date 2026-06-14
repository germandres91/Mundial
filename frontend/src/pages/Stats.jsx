import ChartCard from "../components/charts/ChartCard";
import { BarChartView, LineChartView, RaceChart } from "../components/charts/Charts";
import { Skeleton } from "../components/Skeleton";
import { useRanking, useStatsHits, useStatsRace } from "../hooks/useApi";

export default function Stats() {
  const { data: ranking, isLoading: l1 } = useRanking();
  const { data: hits, isLoading: l2 } = useStatsHits();
  const { data: race, isLoading: l3 } = useStatsRace();

  const loading = l1 || l2 || l3;

  const accumulated = (ranking || []).map((r) => ({
    label: r.nombre,
    value: r.puntos_totales,
  }));

  const hayCarrera = (race?.partidos?.length || 0) > 0;

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-[28rem] w-full rounded-2xl" />
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-80 w-full rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold">Estadísticas</h1>
        <p className="text-sm text-slate-500">Análisis visual del rendimiento.</p>
      </div>

      <ChartCard
        title="Carrera al mundial 🏆"
        subtitle="Puntaje acumulado de cada jugador a medida que avanzan los partidos"
        bodyClassName="h-[26rem]"
      >
        {hayCarrera ? (
          <RaceChart partidos={race.partidos} series={race.series} />
        ) : (
          <div className="flex h-full items-center justify-center text-center text-sm text-slate-500">
            Aún no hay partidos finalizados. La carrera se irá dibujando a medida
            que se jueguen los partidos del Mundial.
          </div>
        )}
      </ChartCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Evolución del ranking"
          subtitle="Puntos por participante (ordenado)"
        >
          <LineChartView data={accumulated} />
        </ChartCard>

        <ChartCard title="Aciertos por participante" subtitle="Partidos acertados">
          <BarChartView data={hits || []} color="#10b981" />
        </ChartCard>
      </div>
    </div>
  );
}
