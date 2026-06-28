import { useEffect, useMemo, useState } from "react";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
import { useMutationWithRefresh, useRoundMatches } from "../hooks/useApi";
import { endpoints } from "../services/api";
import { formatColombia, formatMatchSchedule } from "../utils/dates";

function MatchRow({ match, onSubmitted }) {
  const toast = useToast();
  const [local, setLocal] = useState("");
  const [visitante, setVisitante] = useState("");

  const submit = useMutationWithRefresh(
    () =>
      endpoints.submitRoundPrediction({
        match_id: match.match_id,
        pred_local: Number(local),
        pred_visitante: Number(visitante),
      }),
    {
      onSuccess: (res) => {
        if (res.status === "pending_approval") {
          toast.success("Enviado fuera de plazo — pendiente de aprobación del admin");
        } else {
          toast.success("Predicción registrada. Ya no podrás modificarla.");
        }
        onSubmitted();
      },
      onError: (e) =>
        toast.error(e.response?.data?.detail || "No se pudo enviar la predicción"),
    }
  );

  const isLate = !match.kickoff_open && match.estado === "SCHEDULED";
  const canEdit =
    !match.submitted &&
    !match.pending_approval &&
    match.can_submit &&
    match.estado === "SCHEDULED";

  const fechaLabel = formatMatchSchedule(match);

  return (
    <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-400">{match.fase}</p>
          <p className="font-semibold">
            {match.local} vs {match.visitante}
          </p>
          <p className="text-xs text-slate-500">{fechaLabel}</p>
        </div>
        <StatusBadge status={match.estado} />
      </div>

      {match.submitted ? (
        <div className="rounded-lg bg-emerald-500/10 px-3 py-2 text-sm">
          Tu predicción:{" "}
          <strong>
            {match.pred_local} - {match.pred_visitante}
          </strong>
          {match.locked_at && (
            <span className="ml-2 text-xs text-slate-500">
              (bloqueada{" "}
              {formatColombia(match.locked_at, {
                day: "2-digit",
                month: "short",
                hour: "2-digit",
                minute: "2-digit",
              })}
              )
            </span>
          )}
        </div>
      ) : match.pending_approval ? (
        <div className="rounded-lg bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
          Pendiente de aprobación del administrador (enviaste fuera de plazo).
        </div>
      ) : canEdit ? (
        <div className="space-y-2">
          {isLate && (
            <p className="text-xs text-amber-600 dark:text-amber-400">
              Plazo cerrado: tu envío quedará pendiente de aprobación del administrador.
            </p>
          )}
          {match.fifa_id === "KO-R32-1" && match.kickoff_open && (
            <p className="text-xs text-emerald-600 dark:text-emerald-400">
              Excepción de hoy: puedes enviar tu predicción para Sudáfrica vs Canadá hasta
              medianoche (hora Colombia).
            </p>
          )}
          <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-slate-500">{match.local}</label>
            <input
              type="number"
              min="0"
              max="99"
              className="input w-20 text-center"
              value={local}
              onChange={(e) => setLocal(e.target.value)}
            />
          </div>
          <span className="pb-2 font-bold">-</span>
          <div>
            <label className="mb-1 block text-xs text-slate-500">{match.visitante}</label>
            <input
              type="number"
              min="0"
              max="99"
              className="input w-20 text-center"
              value={visitante}
              onChange={(e) => setVisitante(e.target.value)}
            />
          </div>
          <button
            className="btn-primary"
            disabled={
              submit.isPending ||
              local === "" ||
              visitante === "" ||
              Number(local) < 0 ||
              Number(visitante) < 0
            }
            onClick={() => submit.mutate()}
          >
            Enviar predicción
          </button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          {match.estado !== "SCHEDULED"
            ? "El partido ya se jugó; no se aceptan predicciones."
            : "Plazo cerrado. Contacta al administrador si necesitas enviar tarde."}
        </p>
      )}
    </div>
  );
}

export default function MisPredicciones() {
  const { user, refreshMe } = useAuth();
  const { data: matches, isLoading, refetch } = useRoundMatches();
  const [linking, setLinking] = useState(false);

  useEffect(() => {
    if (user && !user.participant_id) {
      setLinking(true);
      refreshMe().finally(() => setLinking(false));
    }
  }, [user?.id]);

  const byPhase = useMemo(() => {
    const map = {};
    (matches || []).forEach((m) => {
      const f = m.fase || "Eliminatorias";
      if (!map[f]) map[f] = [];
      map[f].push(m);
    });
    return map;
  }, [matches]);

  if (linking) {
    return <p className="text-sm text-slate-500">Vinculando tu cuenta con tu participante…</p>;
  }

  if (!user?.participant_id) {
    return (
      <div className="card max-w-xl">
        <h1 className="text-xl font-bold">Mis predicciones — Eliminatorias</h1>
        <p className="mt-2 text-sm text-slate-500">
          Tu cuenta no está vinculada a un participante. Pide al administrador que
          vincule tu correo con tu nombre en la quiniela.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold">Mis predicciones</h1>
        <p className="text-sm text-slate-500">
          Eliminatorias del Mundial 2026. Cada marcador se envía{" "}
          <strong>una sola vez</strong> y solo antes de que empiece el partido.
        </p>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Cargando partidos…</p>
      ) : !matches?.length ? (
        <div className="card">
          <p className="text-sm text-slate-500">
            Aún no hay partidos de eliminatorias. El administrador debe generar los
            cruces cuando termine la fase anterior.
          </p>
        </div>
      ) : (
        Object.entries(byPhase).map(([fase, items]) => (
          <section key={fase} className="space-y-3">
            <h2 className="text-lg font-semibold">{fase}</h2>
            <div className="grid gap-3 lg:grid-cols-2">
              {items.map((m) => (
                <MatchRow key={m.match_id} match={m} onSubmitted={refetch} />
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}
