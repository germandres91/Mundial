function Tie({ top, bottom, highlight }) {
  return (
    <div
      className={`min-w-[150px] rounded-xl border p-2 text-sm shadow-sm ${
        highlight
          ? "border-amber-400/50 bg-amber-400/10"
          : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800"
      }`}
    >
      <div className="truncate font-medium">{top || "Por definir"}</div>
      <div className="my-1 border-t border-dashed border-slate-300 dark:border-slate-600" />
      <div className="truncate font-medium">{bottom || "Por definir"}</div>
    </div>
  );
}

function Column({ title, children }) {
  return (
    <div className="flex flex-col justify-center gap-6">
      <p className="text-center text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </p>
      <div className="flex flex-col justify-center gap-6">{children}</div>
    </div>
  );
}

/**
 * Diagrama de flujo de eliminatorias proyectado a partir del pronóstico de
 * los 4 primeros puestos del participante.
 */
export default function KnockoutFlow({ top4 }) {
  const byPos = Object.fromEntries(top4.map((t) => [t.posicion, t.equipo]));
  const campeon = byPos[1];
  const sub = byPos[2];
  const tercero = byPos[3];
  const cuarto = byPos[4];

  if (!campeon) {
    return (
      <div className="card text-center text-sm text-slate-500">
        Este participante aún no tiene pronóstico de los primeros puestos.
      </div>
    );
  }

  return (
    <div className="card overflow-x-auto">
      <div className="flex min-w-max items-stretch gap-8 p-2">
        <Column title="Semifinales">
          <Tie top={campeon} bottom={cuarto} />
          <Tie top={sub} bottom={tercero} />
        </Column>

        <Column title="Final">
          <Tie top={campeon} bottom={sub} highlight />
        </Column>

        <Column title="Campeón">
          <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-amber-400/60 bg-gradient-to-b from-amber-400/20 to-amber-500/5 px-6 py-5 text-center">
            <span className="text-4xl">🏆</span>
            <span className="text-lg font-extrabold">{campeon}</span>
            <span className="text-xs text-slate-500">Campeón del Mundo</span>
          </div>
        </Column>

        <Column title="Tercer puesto">
          <Tie top={tercero} bottom={cuarto} />
        </Column>
      </div>
    </div>
  );
}
