import { useRef, useState } from "react";
import ChartCard from "../components/charts/ChartCard";
import { BarChartView } from "../components/charts/Charts";
import StatCard from "../components/StatCard";
import { useToast } from "../context/ToastContext";
import {
  useMutationWithRefresh,
  useParticipants,
  useParticipantStats,
  useParticipantTop4,
} from "../hooks/useApi";
import { endpoints } from "../services/api";

const MEDALS = { 1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣" };

function AddParticipant() {
  const toast = useToast();
  const fileRef = useRef(null);
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [file, setFile] = useState(null);

  const create = useMutationWithRefresh(endpoints.createParticipant, {
    onSuccess: () => {
      toast.success("Participante creado");
      setNombre("");
      setEmail("");
    },
    onError: (e) =>
      toast.error(e?.response?.data?.detail || "No se pudo crear el participante"),
  });

  const importExcel = useMutationWithRefresh(endpoints.importParticipant, {
    onSuccess: (data) => {
      toast.success(
        `Importado: ${data.nombre} · ${data.predicciones_importadas} predicciones`
      );
      setNombre("");
      setEmail("");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
    },
    onError: (e) =>
      toast.error(e?.response?.data?.detail || "No se pudo importar el formulario"),
  });

  return (
    <div className="card space-y-4">
      <div>
        <h2 className="text-lg font-bold">Agregar participante</h2>
        <p className="text-sm text-slate-500">
          Crea un participante manualmente o carga su formulario Excel (mismo
          formato del formulario de apuestas) para llenar todas sus predicciones.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">
            Nombre *
          </label>
          <input
            className="input"
            placeholder="Nombre del participante"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">
            Email (opcional)
          </label>
          <input
            className="input"
            placeholder="se genera automáticamente si lo dejas vacío"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500">
          Formulario Excel (.xlsm / .xlsx)
        </label>
        <input
          ref={fileRef}
          type="file"
          accept=".xlsm,.xlsx"
          className="block w-full text-sm text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-brand-700"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          className="btn-primary px-4 py-2"
          disabled={!nombre || !file || importExcel.isPending}
          onClick={() => importExcel.mutate({ nombre, email, file })}
        >
          {importExcel.isPending ? "Importando…" : "Cargar desde Excel"}
        </button>
        <button
          className="btn-ghost px-4 py-2"
          disabled={!nombre || create.isPending}
          onClick={() =>
            create.mutate({
              nombre,
              email: email || `${nombre.toLowerCase().replace(/\s+/g, ".")}@mundial2026.com`,
            })
          }
        >
          Crear sin predicciones
        </button>
      </div>
    </div>
  );
}

export default function Participant() {
  const { data: participants } = useParticipants();
  const [id, setId] = useState("");
  const numId = id ? Number(id) : null;
  const { data: stats, isLoading } = useParticipantStats(numId);
  const { data: top4 } = useParticipantTop4(numId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold">Participantes</h1>
        <p className="text-sm text-slate-500">
          Agrega participantes y revisa su rendimiento individual.
        </p>
      </div>

      <AddParticipant />

      <div className="card">
        <label className="mb-1 block text-xs font-medium text-slate-500">
          Selecciona un participante
        </label>
        <select className="input max-w-sm" value={id} onChange={(e) => setId(e.target.value)}>
          <option value="">Elige…</option>
          {(participants || []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.nombre}
            </option>
          ))}
        </select>
      </div>

      {!id && (
        <div className="card text-center text-slate-500">
          Selecciona un participante para ver sus estadísticas.
        </div>
      )}

      {id && isLoading && <div className="card text-slate-500">Cargando…</div>}

      {stats && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard title="Puntos totales" value={stats.puntos_totales} icon="🎯" />
            <StatCard
              title="Marcadores exactos"
              value={stats.aciertos_exactos}
              icon="💯"
              accent="emerald"
            />
            <StatCard
              title="Partidos acertados"
              value={stats.partidos_acertados}
              icon="✅"
              accent="amber"
            />
          </div>

          {top4?.length > 0 && (
            <div className="card">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
                Pronóstico de puestos finales
              </h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {top4.map((t) => (
                  <div
                    key={t.posicion}
                    className="flex items-center gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700"
                  >
                    <span className="text-2xl">{MEDALS[t.posicion] || "🏅"}</span>
                    <div>
                      <p className="text-xs text-slate-500">
                        {t.posicion}° puesto · {t.puntos} pts
                      </p>
                      <p className="font-semibold">{t.equipo}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <ChartCard
            title={`Puntos por fase · ${stats.nombre}`}
            subtitle="Distribución del rendimiento"
          >
            <BarChartView data={stats.puntos_por_fase} color="#8b5cf6" />
          </ChartCard>
        </>
      )}
    </div>
  );
}
