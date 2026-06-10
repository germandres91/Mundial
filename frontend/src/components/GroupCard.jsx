export default function GroupCard({ grupo, rows }) {
  return (
    <div className="card animate-fade-in p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-600 text-xs font-bold text-white">
          {grupo}
        </span>
        <span className="text-sm font-semibold">Grupo {grupo}</span>
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[10px] uppercase text-slate-500">
            <th className="py-1 text-left font-medium">Equipo</th>
            <th className="px-1 font-medium">PJ</th>
            <th className="px-1 font-medium">DG</th>
            <th className="px-1 font-medium">Pts</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const qualifies = i < 2;
            return (
              <tr
                key={r.equipo}
                className={`border-t border-slate-100 dark:border-slate-800 ${
                  qualifies ? "font-semibold" : "text-slate-500"
                }`}
              >
                <td className="flex items-center gap-1.5 py-1">
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      qualifies ? "bg-emerald-500" : "bg-slate-300 dark:bg-slate-700"
                    }`}
                  />
                  <span className="truncate">{r.equipo}</span>
                </td>
                <td className="px-1 text-center">{r.pj}</td>
                <td className="px-1 text-center">{r.dg > 0 ? `+${r.dg}` : r.dg}</td>
                <td className="px-1 text-center">{r.pts}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
