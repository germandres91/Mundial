import { useMemo, useState } from "react";
import DataTable from "../components/DataTable";
import StatusBadge from "../components/StatusBadge";
import { SkeletonTable } from "../components/Skeleton";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import {
  useMatches,
  useMutationWithRefresh,
  useParticipants,
  usePredictions,
} from "../hooks/useApi";
import { endpoints } from "../services/api";
import { evaluatePrediction, scoringGoals } from "../utils/scoring";

export default function Predictions() {
  const toast = useToast();
  const { isAdmin } = useAuth();
  const { data: participants } = useParticipants();
  const [participantId, setParticipantId] = useState("");
  const { data: matches, isLoading } = useMatches();
  const { data: predictions } = usePredictions({ participant_id: participantId || null });
  const [drafts, setDrafts] = useState({});

  const [resultDrafts, setResultDrafts] = useState({});

  const predMap = useMemo(() => {
    const map = {};
    (predictions || []).forEach((p) => (map[p.match_id] = p));
    return map;
  }, [predictions]);

  const save = useMutationWithRefresh(endpoints.createPrediction, {
    onSuccess: () => toast.success("Predicción guardada"),
    onError: (e) =>
      toast.error(e.response?.data?.detail || "No se pudo guardar la predicción"),
  });

  const saveResult = useMutationWithRefresh(
    ({ id, payload }) => endpoints.setResult(id, payload),
    {
      onSuccess: () => toast.success("Resultado registrado y ranking actualizado"),
      onError: (e) =>
        toast.error(e.response?.data?.detail || "No se pudo registrar el resultado"),
    }
  );

  const handleSave = (matchId) => {
    if (!participantId) return toast.error("Selecciona un participante");
    const draft = drafts[matchId] || {};
    const existing = predMap[matchId];
    save.mutate({
      participant_id: Number(participantId),
      match_id: matchId,
      pred_local: Number(draft.local ?? existing?.pred_local ?? 0),
      pred_visitante: Number(draft.visitante ?? existing?.pred_visitante ?? 0),
    });
  };

  const handleSaveResult = (match) => {
    const draft = resultDrafts[match.id] || {};
    const local = Number(draft.local ?? match.goles_local ?? 0);
    const visitante = Number(draft.visitante ?? match.goles_visitante ?? 0);
    saveResult.mutate({
      id: match.id,
      payload: { goles_local: local, goles_visitante: visitante, estado: "FINISHED" },
    });
  };

  const setDraft = (matchId, side, value) =>
    setDrafts((d) => ({ ...d, [matchId]: { ...d[matchId], [side]: value } }));

  const setResultDraft = (matchId, side, value) =>
    setResultDrafts((d) => ({ ...d, [matchId]: { ...d[matchId], [side]: value } }));

  const columns = [
    {
      key: "match",
      header: "Partido",
      render: (m) => (
        <div className="font-medium">
          {m.local} <span className="text-slate-500">vs</span> {m.visitante}
          <div className="text-xs text-slate-500">{m.fase}</div>
        </div>
      ),
    },
    { key: "estado", header: "Estado", render: (m) => <StatusBadge status={m.estado} /> },
    {
      key: "resultado",
      header: "Resultado",
      render: (m) => {
        const hasScore = m.goles_local != null && m.goles_visitante != null;
        const isFinished = m.estado === "FINISHED";
        const isLive = m.estado === "LIVE";
        // Vista de admin: permitir registrar/corregir el marcador real.
        if (isAdmin && (isFinished || isLive)) {
          return (
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                className="input w-14 text-center"
                defaultValue={m.goles_local ?? ""}
                onChange={(e) => setResultDraft(m.id, "local", e.target.value)}
              />
              <span className="text-slate-500">-</span>
              <input
                type="number"
                min="0"
                className="input w-14 text-center"
                defaultValue={m.goles_visitante ?? ""}
                onChange={(e) => setResultDraft(m.id, "visitante", e.target.value)}
              />
              <button
                className="btn-primary px-2.5 py-1 text-xs"
                disabled={saveResult.isPending}
                onClick={() => handleSaveResult(m)}
                title="Guardar marcador real y recalcular ranking"
              >
                ✓
              </button>
            </div>
          );
        }
        if (!hasScore) return <span className="text-slate-400">—</span>;
        const gl90 = m.goles_local_90;
        const gv90 = m.goles_visitante_90;
        const has90 = gl90 != null && gv90 != null;
        const diff90 = has90 && (gl90 !== m.goles_local || gv90 !== m.goles_visitante);
        const forPoints = scoringGoals(m);
        return (
          <div className="tabular-nums">
            <span
              className={`font-bold ${isLive ? "text-rose-500" : "text-emerald-500"}`}
            >
              {m.goles_local} - {m.goles_visitante}
            </span>
            {diff90 && forPoints && (
              <p className="mt-0.5 text-[11px] font-medium text-amber-600 dark:text-amber-400">
                Puntos (90&apos;): {forPoints.local} - {forPoints.visitante}
              </p>
            )}
          </div>
        );
      },
    },
    {
      key: "pred",
      header: "Predicción",
      render: (m) => {
        const existing = predMap[m.id];
        const acierto =
          existing && scoringGoals(m)
            ? evaluatePrediction(existing.pred_local, existing.pred_visitante, m)
            : null;
        if (!isAdmin) {
          return existing ? (
            <span className="flex items-center gap-2">
              <span className="font-semibold tabular-nums">
                {existing.pred_local} - {existing.pred_visitante}
              </span>
              {acierto === "exacto" && (
                <span className="badge bg-emerald-500/15 text-emerald-500">Exacto</span>
              )}
              {acierto === "parcial" && (
                <span className="badge bg-amber-500/15 text-amber-500">Acierto</span>
              )}
            </span>
          ) : (
            <span className="text-slate-400">—</span>
          );
        }
        const disabled = m.estado !== "SCHEDULED";
        return (
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              disabled={disabled}
              className="input w-16 text-center"
              defaultValue={existing?.pred_local}
              onChange={(e) => setDraft(m.id, "local", e.target.value)}
            />
            <span className="text-slate-500">-</span>
            <input
              type="number"
              min="0"
              disabled={disabled}
              className="input w-16 text-center"
              defaultValue={existing?.pred_visitante}
              onChange={(e) => setDraft(m.id, "visitante", e.target.value)}
            />
          </div>
        );
      },
    },
    ...(isAdmin
      ? [
          {
            key: "action",
            header: "",
            render: (m) =>
              m.estado === "SCHEDULED" && (
                <button
                  className="btn-primary px-3 py-1.5 text-xs"
                  disabled={save.isPending}
                  onClick={() => handleSave(m.id)}
                >
                  Guardar
                </button>
              ),
          },
        ]
      : []),
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold">Predicciones</h1>
        <p className="text-sm text-slate-500">
          {isAdmin
            ? "Registra las predicciones antes de cada partido y el marcador real cuando finalicen (columna Resultado)."
            : "Consulta las predicciones registradas por cada participante y el resultado real de cada partido."}
        </p>
      </div>

      <div className="card flex flex-wrap items-end gap-4">
        <div className="flex-1 min-w-[220px]">
          <label className="mb-1 block text-xs font-medium text-slate-500">
            Participante
          </label>
          <select
            className="input"
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
      </div>

      {isLoading ? (
        <SkeletonTable />
      ) : (
        <DataTable
          columns={columns}
          data={matches || []}
          emptyMessage="No hay partidos disponibles."
        />
      )}
    </div>
  );
}
