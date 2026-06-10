import ChartCard from "../components/charts/ChartCard";
import { BarChartView, LineChartView } from "../components/charts/Charts";
import { Skeleton } from "../components/Skeleton";
import { useRanking, useStatsHits, useStatsPhases } from "../hooks/useApi";

export default function Stats() {
  const { data: ranking, isLoading: l1 } = useRanking();
  const { data: hits, isLoading: l2 } = useStatsHits();
  const { data: phases, isLoading: l3 } = useStatsPhases();

  const loading = l1 || l2 || l3;

  const accumulated = (ranking || []).map((r) => ({
    label: r.nombre,
    value: r.puntos_totales,
  }));

  if (loading) {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-80 w-full rounded-2xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold">Estadísticas</h1>
        <p className="text-sm text-slate-500">Análisis visual del rendimiento.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Evolución del ranking"
          subtitle="Puntos por participante (ordenado)"
        >
          <LineChartView data={accumulated} />
        </ChartCard>

        <ChartCard title="Puntos acumulados" subtitle="Total por participante">
          <BarChartView data={accumulated} color="#2563eb" />
        </ChartCard>

        <ChartCard title="Aciertos por participante" subtitle="Partidos acertados">
          <BarChartView data={hits || []} color="#10b981" />
        </ChartCard>

        <ChartCard title="Rendimiento por fase" subtitle="Puntos totales por fase">
          <BarChartView data={phases || []} color="#f59e0b" />
        </ChartCard>
      </div>
    </div>
  );
}
