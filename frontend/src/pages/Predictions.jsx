import { useMemo, useState } from "react";
import DataTable from "../components/DataTable";
import StatusBadge from "../components/StatusBadge";
import { SkeletonTable } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import {
  useMatches,
  useMutationWithRefresh,
  useParticipants,
  usePredictions,
} from "../hooks/useApi";
import { endpoints } from "../services/api";

export default function Predictions() {
  const toast = useToast();
  const { data: participants } = useParticipants();
  const [participantId, setParticipantId] = useState("");
  const { data: matches, isLoading } = useMatches();
  const { data: predictions } = usePredictions({ participant_id: participantId || null });
  const [drafts, setDrafts] = useState({});

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

  const setDraft = (matchId, side, value) =>
    setDrafts((d) => ({ ...d, [matchId]: { ...d[matchId], [side]: value } }));

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
      key: "pred",
      header: "Tu predicción",
      render: (m) => {
        const existing = predMap[m.id];
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
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold">Predicciones</h1>
        <p className="text-sm text-slate-500">
          Registra los marcadores antes de que inicie cada partido.
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
