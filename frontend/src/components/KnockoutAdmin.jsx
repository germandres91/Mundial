import { useState } from "react";
import { useToast } from "../context/ToastContext";
import {
  useKnockoutStatus,
  useLatePredictions,
  useMutationWithRefresh,
  useRoundSubmissions,
} from "../hooks/useApi";
import { endpoints } from "../services/api";

const FASES = [
  "Dieciseisavos de final",
  "Octavos de final",
  "Cuartos de final",
  "Semifinales",
  "Final",
];

function CellIcon({ cell }) {
  if (cell.submitted) {
    return (
      <span
        className="text-emerald-600"
        title={`${cell.pred_local ?? "?"}-${cell.pred_visitante ?? "?"}`}
      >
        ✓
      </span>
    );
  }
  if (cell.pending) {
    return <span className="text-amber-500" title="Pendiente de aprobación">⏳</span>;
  }
  return <span className="text-slate-300">—</span>;
}

export default function KnockoutAdmin() {
  const toast = useToast();
  const [faseFilter, setFaseFilter] = useState("");
  const { data: status, refetch: refetchStatus } = useKnockoutStatus();
  const { data: matrix, refetch: refetchMatrix } = useRoundSubmissions(faseFilter || null);
  const { data: lateList, refetch: refetchLate } = useLatePredictions();

  const refreshAll = () => {
    refetchStatus();
    refetchMatrix();
    refetchLate();
  };

  const advanceR32 = useMutationWithRefresh(endpoints.knockoutAdvanceR32, {
    onSuccess: (d) => {
      const msg =
        d.created || d.updated
          ? `Dieciseisavos: ${d.created ?? 0} creados, ${d.updated ?? 0} actualizados`
          : d.message || "Dieciseisavos al día";
      toast.success(msg);
      refreshAll();
    },
    onError: (e) => toast.error(e.response?.data?.detail || "No se pudo publicar"),
  });

  const syncR32 = useMutationWithRefresh(endpoints.knockoutSyncR32, {
    onSuccess: (d) => {
      toast.success(
        `Calendario oficial: ${d.created ?? 0} creados, ${d.updated ?? 0} actualizados`
      );
      refreshAll();
    },
    onError: (e) => toast.error(e.response?.data?.detail || "No se pudo sincronizar"),
  });

  const advanceNext = useMutationWithRefresh(endpoints.knockoutAdvanceNext, {
    onSuccess: (d) => {
      toast.success(
        d.created
          ? `${d.fase}: ${d.created} partidos creados`
          : d.message || "La ronda ya existía"
      );
      refreshAll();
    },
    onError: (e) => toast.error(e.response?.data?.detail || "No se pudo avanzar"),
  });

  const linkUsers = useMutationWithRefresh(endpoints.linkUsersParticipants, {
    onSuccess: (d) => toast.success(`${d.vinculados} cuentas vinculadas a participantes`),
    onError: (e) => toast.error(e.response?.data?.detail || "Error al vincular"),
  });

  const approve = useMutationWithRefresh(
    (id) => endpoints.approveLatePrediction(id),
    {
      onSuccess: () => {
        toast.success("Predicción aprobada");
        refreshAll();
      },
      onError: (e) => toast.error(e.response?.data?.detail || "No se pudo aprobar"),
    }
  );

  const reject = useMutationWithRefresh(
    (id) => endpoints.rejectLatePrediction(id),
    {
      onSuccess: () => {
        toast.success("Solicitud rechazada");
        refreshAll();
      },
      onError: (e) => toast.error(e.response?.data?.detail || "No se pudo rechazar"),
    }
  );

  return (
    <div className="card space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">Eliminatorias — predicciones por ronda</h2>
          <p className="text-sm text-slate-500">
            Genera cruces, revisa quién envió marcadores y aprueba envíos fuera de plazo.
          </p>
        </div>
        <button className="btn-ghost text-sm" onClick={() => linkUsers.mutate()}>
          🔗 Vincular cuentas
        </button>
      </div>

      {status && (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {FASES.map((f) => {
            const s = status[f] || { total: 0, finished: 0, scheduled: 0 };
            return (
              <div
                key={f}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700"
              >
                <div className="font-medium">{f}</div>
                <div className="text-xs text-slate-500">
                  {s.total} partidos · {s.finished} finalizados · {s.scheduled} programados
                </div>
              </div>
            );
          })}
          {"clasificados_disponibles" in status && (
            <div className="rounded-lg bg-slate-100 px-3 py-2 text-sm dark:bg-slate-800">
              Clasificados desde grupos:{" "}
              <strong>{status.clasificados_disponibles}</strong> / 32
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          className="btn-primary"
          disabled={advanceR32.isPending}
          onClick={() => {
            if (
              window.confirm(
                "¿Publicar los 16 dieciseisavos con cruces y horarios oficiales del Mundial?"
              )
            ) {
              advanceR32.mutate();
            }
          }}
        >
          {advanceR32.isPending ? "Publicando…" : "⚽ Publicar dieciseisavos"}
        </button>
        <button
          className="btn-ghost text-sm"
          disabled={syncR32.isPending}
          onClick={() => syncR32.mutate()}
        >
          {syncR32.isPending ? "Sincronizando…" : "🔄 Actualizar calendario oficial"}
        </button>
        {FASES.slice(0, -1).map((f) => (
          <button
            key={f}
            className="btn-ghost text-sm"
            disabled={advanceNext.isPending}
            onClick={() => {
              if (window.confirm(`¿Avanzar a la siguiente ronda desde ${f}?`)) {
                advanceNext.mutate(f);
              }
            }}
          >
            Siguiente ronda ← {f.split(" ")[0]}
          </button>
        ))}
      </div>

      {(lateList?.length ?? 0) > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Aprobaciones pendientes</h3>
          <div className="space-y-2">
            {lateList.map((r) => (
              <div
                key={r.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm dark:border-amber-900/50 dark:bg-amber-950/30"
              >
                <div>
                  <strong>{r.participant_nombre}</strong> — {r.partido}{" "}
                  <span className="text-slate-500">({r.fase})</span>
                  <div className="font-mono">
                    Predicción: {r.pred_local} - {r.pred_visitante}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    className="btn-primary px-3 py-1 text-sm"
                    disabled={approve.isPending}
                    onClick={() => approve.mutate(r.id)}
                    title="Aprobar"
                  >
                    ✓ Aprobar
                  </button>
                  <button
                    className="btn-ghost px-3 py-1 text-sm text-rose-500"
                    disabled={reject.isPending}
                    onClick={() => reject.mutate(r.id)}
                    title="Rechazar"
                  >
                    ✗
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">Matriz de envíos</h3>
          <select
            className="input w-auto text-sm"
            value={faseFilter}
            onChange={(e) => setFaseFilter(e.target.value)}
          >
            <option value="">Todas las fases</option>
            {FASES.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </div>

        {!matrix?.matches?.length ? (
          <p className="text-sm text-slate-500">
            No hay partidos de eliminatorias aún. Genera los dieciseisavos primero.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800">
                  <th className="sticky left-0 z-10 bg-slate-50 px-2 py-2 text-left dark:bg-slate-800">
                    Participante
                  </th>
                  {matrix.matches.map((m) => (
                    <th
                      key={m.id}
                      className="px-1 py-2 text-center font-normal"
                      title={`${m.local} vs ${m.visitante}`}
                    >
                      <div className="max-w-[4.5rem] truncate">{m.local?.slice(0, 3)}</div>
                      <div className="text-[10px] text-slate-400">vs</div>
                      <div className="max-w-[4.5rem] truncate">{m.visitante?.slice(0, 3)}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.participants.map((p) => (
                  <tr key={p.participant_id} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="sticky left-0 z-10 bg-white px-2 py-1.5 font-medium dark:bg-slate-900">
                      {p.nombre}
                    </td>
                    {p.cells.map((cell, idx) => (
                      <td key={idx} className="px-1 py-1.5 text-center">
                        <CellIcon cell={cell} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-2 text-xs text-slate-500">
          ✓ enviado · ⏳ pendiente de aprobación · — sin enviar
        </p>
      </div>
    </div>
  );
}
