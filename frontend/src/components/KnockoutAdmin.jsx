import { useState } from "react";
import { useToast } from "../context/ToastContext";
import {
  useKnockoutStatus,
  useMutationWithRefresh,
  useRoundSubmissions,
} from "../hooks/useApi";
import { endpoints } from "../services/api";

const FASES = [
  "Dieciseisavos de final",
  "Octavos de final",
  "Cuartos de final",
  "Semifinales",
  "Tercer puesto",
  "Final",
];

const ADVANCE_FROM = [
  {
    fromFase: "Dieciseisavos de final",
    label: "Publicar octavos",
    hint: "Sincroniza resultados de internet y crea los 8 partidos de octavos con las llaves FIFA.",
  },
  {
    fromFase: "Octavos de final",
    label: "Publicar cuartos",
    hint: "Crea los 4 partidos de cuartos de final desde los ganadores de octavos.",
  },
  {
    fromFase: "Cuartos de final",
    label: "Publicar semifinales",
    hint: "Crea o corrige las 2 semifinales con el cuadro FIFA (1º vs 3º y 2º vs 4º de cuartos).",
  },
  {
    fromFase: "Semifinales",
    label: "Publicar final y tercer puesto",
    hint: "Crea la final (ganadores) y el partido por el tercer puesto (perdedores de semis).",
  },
];

function MatrixCell({ cell }) {
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
  return <span className="text-slate-300">—</span>;
}

export default function KnockoutAdmin() {
  const toast = useToast();
  const [faseFilter, setFaseFilter] = useState("");
  const [savingBackup, setSavingBackup] = useState(false);
  const { data: status, refetch: refetchStatus } = useKnockoutStatus();
  const { data: matrix, refetch: refetchMatrix } = useRoundSubmissions(faseFilter || null);

  const refreshAll = () => {
    refetchStatus();
    refetchMatrix();
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

  const syncResults = useMutationWithRefresh(endpoints.knockoutSyncResults, {
    onSuccess: (d) => {
      const s = d.sync || {};
      toast.success(
        `Resultados sincronizados: ${s.updated ?? 0} partidos actualizados desde internet`
      );
      refreshAll();
    },
    onError: (e) => toast.error(e.response?.data?.detail || "No se pudo sincronizar"),
  });

  const advanceNext = useMutationWithRefresh(endpoints.knockoutAdvanceNext, {
    onSuccess: (d) => {
      const sync = d.sync?.sync;
      const syncNote = sync ? ` · ${sync.updated ?? 0} resultados desde internet` : "";
      if (d.created) {
        toast.success(`${d.fase}: ${d.created} partidos creados${syncNote}`);
      } else if (d.updated) {
        toast.success(d.message || `${d.fase}: ${d.updated} partidos corregidos${syncNote}`);
      } else {
        toast.success(d.message || "La ronda ya existía");
      }
      refreshAll();
    },
    onError: (e) => toast.error(e.response?.data?.detail || "No se pudo avanzar"),
  });

  const linkUsers = useMutationWithRefresh(endpoints.linkUsersParticipants, {
    onSuccess: (d) => toast.success(`${d.vinculados} cuentas vinculadas a participantes`),
    onError: (e) => toast.error(e.response?.data?.detail || "Error al vincular"),
  });

  const handleSaveBackup = async () => {
    setSavingBackup(true);
    try {
      const res = await endpoints.createBackup();
      const blob = await endpoints.downloadBackup();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "backup.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(
        `Respaldo guardado: ${res.predicciones} predicciones (${res.puntajes_guardados ?? 0} puntajes, ${res.resultados_partidos ?? 0} resultados). Descargado backup.json`
      );
    } catch (e) {
      toast.error(e.response?.data?.detail || "No se pudo guardar el respaldo");
    } finally {
      setSavingBackup(false);
    }
  };

  return (
    <div className="card space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">Eliminatorias — predicciones por ronda</h2>
          <p className="text-sm text-slate-500">
            Genera cruces y revisa quién envió marcadores de eliminatorias.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-ghost text-sm" onClick={() => linkUsers.mutate()}>
            🔗 Vincular cuentas
          </button>
          <button
            className="btn-primary text-sm"
            disabled={savingBackup}
            onClick={handleSaveBackup}
          >
            {savingBackup ? "Guardando…" : "💾 Guardar predicciones"}
          </button>
        </div>
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
          {syncR32.isPending ? "Sincronizando…" : "🔄 Actualizar calendario R32"}
        </button>
        <button
          className="btn-ghost text-sm"
          disabled={syncResults.isPending}
          onClick={() => syncResults.mutate()}
          title="Consulta ESPN/API y actualiza marcadores, penales y ganadores"
        >
          {syncResults.isPending ? "Consultando…" : "🌐 Sincronizar resultados (internet)"}
        </button>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Generar siguiente ronda
        </p>
        <div className="flex flex-wrap gap-2">
          {ADVANCE_FROM.map(({ fromFase, label, hint }) => {
            const idx = FASES.indexOf(fromFase);
            const phaseStatus = status?.[fromFase];
            const nextPhase = FASES[idx + 1];
            const nextStatus = status?.[nextPhase];
            const canAdvance =
              phaseStatus?.total > 0 &&
              phaseStatus?.finished === phaseStatus?.total &&
              (nextStatus?.total ?? 0) === 0;
            return (
              <button
                key={fromFase}
                className={canAdvance ? "btn-primary text-sm" : "btn-ghost text-sm"}
                disabled={advanceNext.isPending}
                title={hint}
                onClick={() => {
                  if (
                    window.confirm(
                      `${hint}\n\n¿Continuar con «${label}»?`
                    )
                  ) {
                    advanceNext.mutate(fromFase);
                  }
                }}
              >
                {advanceNext.isPending ? "Procesando…" : `▶ ${label}`}
              </button>
            );
          })}
        </div>
        <p className="text-xs text-slate-500">
          Cada botón consulta internet, verifica ganadores y publica la ronda siguiente con el
          calendario FIFA. Empieza con «Publicar octavos» cuando terminen los dieciseisavos.
        </p>
      </div>

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
                        <MatrixCell cell={cell} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-2 text-xs text-slate-500">✓ enviado · — sin enviar</p>
      </div>
    </div>
  );
}
