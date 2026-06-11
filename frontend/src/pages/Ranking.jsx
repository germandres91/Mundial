import DataTable from "../components/DataTable";
import { SkeletonTable } from "../components/Skeleton";
import { useRanking } from "../hooks/useApi";
import { endpoints } from "../services/api";

const MEDALS = { 1: "🥇", 2: "🥈", 3: "🥉" };

export default function Ranking() {
  const { data, isLoading } = useRanking();
  const hayEnVivo = Array.isArray(data) && data.some((r) => r.provisional);

  const columns = [
    {
      key: "posicion",
      header: "#",
      className: "w-12 text-center sm:w-16",
      render: (r) => (
        <span className="text-lg font-bold">{MEDALS[r.posicion] || r.posicion}</span>
      ),
    },
    {
      key: "nombre",
      header: "Participante",
      render: (r) => (
        <div>
          <span className="font-semibold">{r.nombre}</span>
          {r.provisional && (
            <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-2 py-0.5 align-middle text-[10px] font-semibold text-rose-500">
              <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-rose-500" />
              +{r.puntos_en_vivo} en vivo
            </span>
          )}
          {/* Detalle compacto solo en móvil */}
          <span className="mt-0.5 block text-xs text-slate-500 sm:hidden">
            {r.aciertos_exactos} exactos · {r.partidos_acertados} aciertos
            {r.puntos_posiciones ? ` · +${r.puntos_posiciones} bonus` : ""}
          </span>
        </div>
      ),
    },
    {
      key: "puntos_totales",
      header: "Puntos",
      className: "text-center",
      render: (r) => (
        <span
          className={`badge ${
            r.provisional
              ? "bg-rose-500/15 text-rose-500"
              : "bg-brand-500/15 text-brand-400"
          }`}
        >
          {r.puntos_totales}
        </span>
      ),
    },
    {
      key: "puntos_posiciones",
      header: "Bonus",
      className: "hidden text-center sm:table-cell",
      render: (r) => (
        <span className={r.puntos_posiciones ? "font-semibold text-amber-500" : "text-slate-400"}>
          {r.puntos_posiciones ? `+${r.puntos_posiciones}` : "—"}
        </span>
      ),
    },
    {
      key: "aciertos_exactos",
      header: "Exactos",
      className: "hidden text-center sm:table-cell",
    },
    {
      key: "partidos_acertados",
      header: "Aciertos",
      className: "hidden text-center sm:table-cell",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold">Ranking</h1>
          <p className="text-sm text-slate-500">Clasificación general del concurso.</p>
          {hayEnVivo && (
            <p className="mt-1 flex items-center gap-1.5 text-xs font-medium text-rose-500">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-rose-500" />
              Incluye puntos provisionales de partidos en vivo (pueden cambiar).
            </p>
          )}
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
