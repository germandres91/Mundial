import { useMemo, useState } from "react";
import DataTable from "../components/DataTable";
import Modal from "../components/Modal";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../context/ToastContext";
import {
  useAudit,
  useFinalPositions,
  useMatches,
  useMutationWithRefresh,
  useRules,
  useSyncStatus,
  useUsers,
} from "../hooks/useApi";
import { endpoints } from "../services/api";

const POSITION_LABELS = {
  1: "1er puesto (Campeón)",
  2: "2do puesto (Subcampeón)",
  3: "3er puesto",
  4: "4to puesto",
};

function ActionButton({ label, icon, onClick, pending }) {
  return (
    <button className="btn-ghost justify-start" onClick={onClick} disabled={pending}>
      <span>{icon}</span> {label}
    </button>
  );
}

const PROVIDER_LABEL = {
  mock: "Datos de prueba (mock)",
  espn: "ESPN (tiempo real)",
  football_data: "football-data.org",
  api_football: "API-Football",
  worldcup_api: "World Cup API",
};

function Stat({ label, value, tone = "" }) {
  return (
    <div className="rounded-lg bg-slate-100 px-3 py-2 text-center dark:bg-slate-800">
      <div className={`text-xl font-bold ${tone}`}>{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

function SyncStatus() {
  const { data, isLoading } = useSyncStatus();

  if (isLoading || !data) {
    return (
      <div className="card">
        <h2 className="mb-1 font-semibold">Estado de sincronización</h2>
        <p className="text-sm text-slate-500">Cargando…</p>
      </div>
    );
  }

  const ready = data.provider_listo;
  const m = data.partidos || {};
  const last = data.ultima_sync;
  const lastWhen = last?.created_at
    ? new Date(last.created_at).toLocaleString("es-CO", {
        timeZone: "America/Bogota",
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }) + " (hora COL)"
    : null;

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold">Estado de sincronización</h2>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
            ready
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
              : "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
          }`}
        >
          {ready ? "● Listo" : "● Falta configurar"}
        </span>
      </div>

      <div className="mb-3 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
        <div className="flex justify-between">
          <span className="text-slate-500">Proveedor</span>
          <span className="font-medium">
            {PROVIDER_LABEL[data.provider] || data.provider}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Competición</span>
          <span className="font-medium">{data.competition}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">API key</span>
          <span className="font-medium">
            {!data.requiere_key
              ? "No requerida"
              : data.api_key_configurada
              ? "Configurada"
              : "Falta"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Automática</span>
          <span className="font-medium">
            {data.sync_habilitada
              ? data.intervalo_vivo_segundos
                ? `En vivo: ${data.intervalo_vivo_segundos}s · normal: ${data.intervalo_minutos} min`
                : `Cada ${data.intervalo_minutos} min`
              : "Desactivada"}
          </span>
        </div>
        {data.api_partidos_ahora != null && (
          <div className="flex justify-between sm:col-span-2">
            <span className="text-slate-500">API ahora</span>
            <span className="font-medium">
              {data.api_partidos_ahora} partidos en{" "}
              {PROVIDER_LABEL[data.provider] || data.provider}
            </span>
          </div>
        )}
      </div>

      {data.api_error && (
        <p className="mb-3 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-600 dark:text-amber-400">
          ⚠️ {data.api_error}
        </p>
      )}

      <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Partidos" value={m.total ?? 0} />
        <Stat label="Programados" value={m.programados ?? 0} />
        <Stat
          label="En vivo"
          value={m.en_vivo ?? 0}
          tone={m.en_vivo ? "text-rose-500" : ""}
        />
        <Stat
          label="Finalizados"
          value={m.finalizados ?? 0}
          tone="text-emerald-600 dark:text-emerald-400"
        />
      </div>

      <div className="rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
        <div className="mb-0.5 text-xs font-semibold uppercase text-slate-400">
          Última sincronización
        </div>
        {last ? (
          <>
            <div className="text-slate-700 dark:text-slate-200">{last.detalle}</div>
            <div className="text-xs text-slate-500">{lastWhen}</div>
          </>
        ) : (
          <div className="text-slate-500">Aún no se ha ejecutado.</div>
        )}
      </div>

      {!ready && (
        <p className="mt-3 text-xs text-amber-600 dark:text-amber-400">
          Configura <code>FOOTBALL_PROVIDER=football_data</code> y
          <code> FOOTBALL_API_KEY</code> en el backend para traer resultados reales.
        </p>
      )}
    </div>
  );
}

function UsersManager() {
  const toast = useToast();
  const { data: users } = useUsers();
  const [form, setForm] = useState({
    nombre: "",
    email: "",
    password: "",
    role: "PARTICIPANT",
  });

  const create = useMutationWithRefresh(endpoints.createUser, {
    onSuccess: () => {
      toast.success("Usuario creado");
      setForm({ nombre: "", email: "", password: "", role: "PARTICIPANT" });
    },
    onError: (e) => toast.error(e.response?.data?.detail || "No se pudo crear el usuario"),
  });

  const remove = useMutationWithRefresh(endpoints.deleteUser, {
    onSuccess: () => toast.success("Usuario eliminado"),
    onError: (e) => toast.error(e.response?.data?.detail || "No se pudo eliminar"),
  });

  const resetPass = useMutationWithRefresh(
    ({ id, password }) => endpoints.resetUserPassword(id, password),
    {
      onSuccess: () => toast.success("Contraseña actualizada"),
      onError: (e) => toast.error(e.response?.data?.detail || "No se pudo cambiar"),
    }
  );

  const roleLabel = (r) => (r === "ADMIN" ? "Administrador" : "Solo lectura");

  const [saving, setSaving] = useState(false);
  const handleBackup = async () => {
    setSaving(true);
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
        `Respaldo guardado: ${res.usuarios} usuarios, ${res.predicciones} predicciones. Se descargó backup.json`
      );
    } catch (e) {
      toast.error(e.response?.data?.detail || "No se pudo guardar el respaldo");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">Usuarios con acceso</h2>
        <button className="btn-primary" disabled={saving} onClick={handleBackup}>
          {saving ? "Guardando…" : "💾 Guardar usuarios"}
        </button>
      </div>
      <p className="mb-3 text-sm text-slate-500">
        Crea cuentas para quienes compartirás el link. Por defecto son de
        <strong> solo lectura</strong>; solo el administrador puede editar.
        <br />
        <span className="text-xs">
          <strong>Guardar usuarios</strong> crea un respaldo (cuentas, correos,
          predicciones y top 4) y descarga <code>backup.json</code>. Envíalo para
          dejarlo permanente y que no se pierda en futuras mejoras.
        </span>
      </p>

      <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <input
          className="input"
          placeholder="Nombre"
          value={form.nombre}
          onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
        />
        <input
          className="input"
          placeholder="Correo"
          value={form.email}
          onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
        />
        <input
          className="input"
          type="text"
          placeholder="Contraseña (mín. 6)"
          value={form.password}
          onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
        />
        <select
          className="input"
          value={form.role}
          onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
        >
          <option value="PARTICIPANT">Solo lectura</option>
          <option value="ADMIN">Administrador</option>
        </select>
        <button
          className="btn-primary"
          disabled={create.isPending || !form.nombre || !form.email || form.password.length < 6}
          onClick={() => create.mutate(form)}
        >
          Crear usuario
        </button>
      </div>

      <DataTable
        columns={[
          { key: "nombre", header: "Nombre" },
          { key: "email", header: "Correo" },
          { key: "role", header: "Rol", render: (u) => roleLabel(u.role) },
          {
            key: "acciones",
            header: "",
            render: (u) => (
              <div className="flex gap-2">
                <button
                  className="btn-ghost px-2 py-1 text-xs"
                  onClick={() => {
                    const pwd = window.prompt(`Nueva contraseña para ${u.email}:`);
                    if (pwd && pwd.length >= 6) resetPass.mutate({ id: u.id, password: pwd });
                    else if (pwd) toast.error("Mínimo 6 caracteres");
                  }}
                >
                  🔑 Clave
                </button>
                <button
                  className="btn-ghost px-2 py-1 text-xs text-rose-500"
                  onClick={() => {
                    if (window.confirm(`¿Eliminar a ${u.email}?`)) remove.mutate(u.id);
                  }}
                >
                  🗑️
                </button>
              </div>
            ),
          },
        ]}
        data={users || []}
        emptyMessage="Sin usuarios."
      />
    </div>
  );
}

function FinalPositionsManager() {
  const toast = useToast();
  const { data } = useFinalPositions();
  const { data: matches } = useMatches();
  const [draft, setDraft] = useState(null);

  const rows = draft ?? data?.posiciones ?? [];

  const teamOptions = useMemo(() => {
    const set = new Set();
    (matches || []).forEach((m) => {
      if (m.local) set.add(m.local);
      if (m.visitante) set.add(m.visitante);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [matches]);

  const save = useMutationWithRefresh(endpoints.setFinalPositions, {
    onSuccess: (res) => {
      toast.success(`Posiciones guardadas (${res.aciertos} aciertos)`);
      setDraft(null);
    },
    onError: (e) => toast.error(e.response?.data?.detail || "No se pudo guardar"),
  });

  const setEquipo = (posicion, equipo) =>
    setDraft(
      rows.map((r) => (r.posicion === posicion ? { ...r, equipo } : { ...r }))
    );

  return (
    <div className="card">
      <h2 className="mb-1 font-semibold">Posiciones finales del Mundial</h2>
      <p className="mb-3 text-sm text-slate-500">
        Al terminar el torneo, registra quién quedó en cada puesto. Se otorga el
        bonus a quienes lo acertaron y se recalcula el ranking.
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        {rows.map((row) => (
          <div key={row.posicion} className="flex flex-col gap-1">
            <label className="flex items-center justify-between text-sm font-medium">
              <span>{POSITION_LABELS[row.posicion]}</span>
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                {row.puntos} pts
              </span>
            </label>
            <input
              className="input"
              list="team-options"
              placeholder="Equipo…"
              value={row.equipo || ""}
              onChange={(e) => setEquipo(row.posicion, e.target.value)}
            />
          </div>
        ))}
      </div>

      <datalist id="team-options">
        {teamOptions.map((t) => (
          <option key={t} value={t} />
        ))}
      </datalist>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          className="btn-primary"
          disabled={save.isPending || rows.length === 0}
          onClick={() =>
            save.mutate(
              rows.map((r) => ({ posicion: r.posicion, equipo: (r.equipo || "").trim() }))
            )
          }
        >
          Guardar posiciones
        </button>
        {draft && (
          <button className="btn-ghost" onClick={() => setDraft(null)}>
            Descartar cambios
          </button>
        )}
      </div>
    </div>
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

  const sync = useMutationWithRefresh(endpoints.triggerSync, {
    onSuccess: (d) =>
      toast.success(
        `Sync: ${d.recibidos ?? "?"} recibidos, ${d.actualizados} actualizados, ${d.en_vivo_horario ?? 0} en vivo`
      ),
    onError: (e) => toast.error(e.response?.data?.detail || "Error en la sincronización"),
  });
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
  const resetTournament = useMutationWithRefresh(
    endpoints.resetTournament,
    mkHandlers((d) => `Torneo reiniciado: ${d.schedule_created} partidos creados`)
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
          Gestión de usuarios, sincronización, importaciones y reglas.
        </p>
      </div>

      <UsersManager />

      <SyncStatus />

      <FinalPositionsManager />

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-3 font-semibold">Acciones</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            <ActionButton label="Sincronizar resultados" icon="🔄" onClick={sync.mutate} pending={sync.isPending} />
            <ActionButton label="Importar calendario" icon="📅" onClick={impCal.mutate} pending={impCal.isPending} />
            <ActionButton label="Importar predicciones" icon="📥" onClick={impPred.mutate} pending={impPred.isPending} />
            <ActionButton label="Importar reglas" icon="📏" onClick={impRules.mutate} pending={impRules.isPending} />
            <ActionButton label="Recalcular ranking" icon="🧮" onClick={recalc.mutate} pending={recalc.isPending} />
            <ActionButton
              label="Resetear torneo oficial"
              icon="♻️"
              pending={resetTournament.isPending}
              onClick={() => {
                if (
                  window.confirm(
                    "Esto borra partidos/predicciones/ranking y recarga el torneo oficial. Conserva los usuarios. ¿Continuar?"
                  )
                ) {
                  resetTournament.mutate();
                }
              }}
            />
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
