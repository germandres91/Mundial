import DataTable from "../components/DataTable";
import { SkeletonTable } from "../components/Skeleton";
import { useRanking } from "../hooks/useApi";
import { endpoints } from "../services/api";

const MEDALS = { 1: "🥇", 2: "🥈", 3: "🥉" };

export default function Ranking() {
  const { data, isLoading } = useRanking();

  const columns = [
    {
      key: "posicion",
      header: "#",
      className: "w-16 text-center",
      render: (r) => (
        <span className="text-lg font-bold">{MEDALS[r.posicion] || r.posicion}</span>
      ),
    },
    {
      key: "nombre",
      header: "Participante",
      render: (r) => <span className="font-semibold">{r.nombre}</span>,
    },
    {
      key: "puntos_totales",
      header: "Puntos",
      render: (r) => (
        <span className="badge bg-brand-500/15 text-brand-400">{r.puntos_totales}</span>
      ),
    },
    { key: "aciertos_exactos", header: "Exactos", className: "text-center" },
    { key: "partidos_acertados", header: "Aciertos", className: "text-center" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold">Ranking</h1>
          <p className="text-sm text-slate-500">Clasificación general del concurso.</p>
        </div>
        <a
          href={endpoints.exportUrl("ranking.xlsx")}
          className="btn-ghost px-3 py-2 text-sm"
          target="_blank"
          rel="noreferrer"
        >
          ⬇️ Exportar Excel
        </a>
      </div>

      {isLoading ? (
        <SkeletonTable rows={8} />
      ) : (
        <DataTable
          columns={columns}
          data={data || []}
          emptyMessage="Aún no hay puntajes registrados."
        />
      )}
    </div>
  );
}
