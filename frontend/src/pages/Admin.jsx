import { useState } from "react";
import DataTable from "../components/DataTable";
import Modal from "../components/Modal";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../context/ToastContext";
import {
  useAudit,
  useMatches,
  useMutationWithRefresh,
  useRules,
} from "../hooks/useApi";
import { endpoints } from "../services/api";

function ActionButton({ label, icon, onClick, pending }) {
  return (
    <button className="btn-ghost justify-start" onClick={onClick} disabled={pending}>
      <span>{icon}</span> {label}
    </button>
  );
}

export default function Admin() {
  const toast = useToast();
  const { data: rules } = useRules();
  const { data: audit } = useAudit();
  const { data: matches } = useMatches({ estado: "SCHEDULED" });
  const [resultModal, setResultModal] = useState(null);
  const [score, setScore] = useState({ local: 0, visitante: 0 });

  const mkHandlers = (successMsg) => ({
    onSuccess: (data) =>
      toast.success(typeof successMsg === "function" ? successMsg(data) : successMsg),
    onError: (e) => toast.error(e.response?.data?.detail || "Error en la operación"),
  });

  const sync = useMutationWithRefresh(
    endpoints.triggerSync,
    mkHandlers("Sincronización ejecutada")
  );
  const impCal = useMutationWithRefresh(
    endpoints.importCalendar,
    mkHandlers((d) => `Calendario importado (${d.partidos})`)
  );
  const impPred = useMutationWithRefresh(
    endpoints.importPredictions,
    mkHandlers((d) => `Predicciones importadas (${d.predicciones_importadas})`)
  );
  const impRules = useMutationWithRefresh(
    endpoints.importRules,
    mkHandlers("Reglas importadas")
  );
  const recalc = useMutationWithRefresh(
    endpoints.recalculateRanking,
    mkHandlers("Ranking recalculado")
  );
  const updateRule = useMutationWithRefresh(
    ({ code, puntos }) => endpoints.updateRule(code, { puntos }),
    { onSuccess: () => toast.success("Regla actualizada") }
  );
  const setResult = useMutationWithRefresh(
    ({ id, payload }) => endpoints.setResult(id, payload),
    {
      onSuccess: () => {
        toast.success("Resultado registrado");
        setResultModal(null);
      },
      onError: (e) => toast.error(e.response?.data?.detail || "Error"),
    }
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold">Administración</h1>
        <p className="text-sm text-slate-500">
          Gestión de sincronización, importaciones y reglas.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-3 font-semibold">Acciones</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            <ActionButton label="Sincronizar resultados" icon="🔄" onClick={sync.mutate} pending={sync.isPending} />
            <ActionButton label="Importar calendario" icon="📅" onClick={impCal.mutate} pending={impCal.isPending} />
            <ActionButton label="Importar predicciones" icon="📥" onClick={impPred.mutate} pending={impPred.isPending} />
            <ActionButton label="Importar reglas" icon="📏" onClick={impRules.mutate} pending={impRules.isPending} />
            <ActionButton label="Recalcular ranking" icon="🧮" onClick={recalc.mutate} pending={recalc.isPending} />
          </div>
        </div>

        <div className="card">
          <h2 className="mb-3 font-semibold">Exportaciones</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              ["ranking.xlsx", "Ranking (Excel)", "🏆"],
              ["results.xlsx", "Resultados (Excel)", "⚽"],
              ["predictions.xlsx", "Predicciones (Excel)", "🎯"],
              ["summary.pdf", "Resumen (PDF)", "📄"],
            ].map(([kind, label, icon]) => (
              <a
                key={kind}
                href={endpoints.exportUrl(kind)}
                target="_blank"
                rel="noreferrer"
                className="btn-ghost justify-start"
              >
                <span>{icon}</span> {label}
              </a>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="mb-3 font-semibold">Registrar resultado</h2>
        {matches?.length ? (
          <div className="flex flex-wrap gap-2">
            {matches.map((m) => (
              <button
                key={m.id}
                className="btn-ghost px-3 py-1.5 text-xs"
                onClick={() => {
                  setResultModal(m);
                  setScore({ local: 0, visitante: 0 });
                }}
              >
                {m.local} vs {m.visitante}
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No hay partidos programados.</p>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <h2 className="mb-3 font-semibold">Reglas de puntaje</h2>
          <DataTable
            columns={[
              { key: "descripcion", header: "Regla" },
              {
                key: "puntos",
                header: "Puntos",
                render: (r) => (
                  <input
                    type="number"
                    className="input w-20"
                    defaultValue={r.puntos}
                    onBlur={(e) =>
                      Number(e.target.value) !== r.puntos &&
                      updateRule.mutate({ code: r.code, puntos: Number(e.target.value) })
                    }
                  />
                ),
              },
            ]}
            data={rules || []}
          />
        </div>

        <div>
          <h2 className="mb-3 font-semibold">Auditoría reciente</h2>
          <DataTable
            columns={[
              { key: "accion", header: "Acción" },
              { key: "actor", header: "Actor" },
              { key: "detalle", header: "Detalle" },
            ]}
            data={(audit || []).slice(0, 10)}
            emptyMessage="Sin registros."
          />
        </div>
      </div>

      <Modal
        open={!!resultModal}
        onClose={() => setResultModal(null)}
        title={resultModal ? `${resultModal.local} vs ${resultModal.visitante}` : ""}
        footer={
          <>
            <button className="btn-ghost" onClick={() => setResultModal(null)}>
              Cancelar
            </button>
            <button
              className="btn-primary"
              disabled={setResult.isPending}
              onClick={() =>
                setResult.mutate({
                  id: resultModal.id,
                  payload: {
                    goles_local: Number(score.local),
                    goles_visitante: Number(score.visitante),
                    estado: "FINISHED",
                  },
                })
              }
            >
              Guardar resultado
            </button>
          </>
        }
      >
        {resultModal && (
          <div className="flex items-center justify-center gap-3">
            <div className="text-center">
              <p className="mb-1 text-sm">{resultModal.local}</p>
              <input
                type="number"
                min="0"
                className="input w-20 text-center text-xl"
                value={score.local}
                onChange={(e) => setScore((s) => ({ ...s, local: e.target.value }))}
              />
            </div>
            <span className="text-2xl font-bold">-</span>
            <div className="text-center">
              <p className="mb-1 text-sm">{resultModal.visitante}</p>
              <input
                type="number"
                min="0"
                className="input w-20 text-center text-xl"
                value={score.visitante}
                onChange={(e) => setScore((s) => ({ ...s, visitante: e.target.value }))}
              />
            </div>
          </div>
        )}
        {resultModal && (
          <div className="text-center">
            <StatusBadge status={resultModal.estado} />
          </div>
        )}
      </Modal>
    </div>
  );
}
