export default function StatCard({ title, value, subtitle, icon, accent = "brand" }) {
  const accents = {
    brand: "from-brand-500/20 to-brand-600/5 text-brand-400",
    emerald: "from-emerald-500/20 to-emerald-600/5 text-emerald-400",
    amber: "from-amber-500/20 to-amber-600/5 text-amber-400",
    rose: "from-rose-500/20 to-rose-600/5 text-rose-400",
  };
  return (
    <div className="card flex items-center gap-4 animate-fade-in">
      <div
        className={`grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br text-xl ${accents[accent]}`}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {title}
        </p>
        <p className="truncate text-2xl font-bold">{value}</p>
        {subtitle && (
          <p className="truncate text-xs text-slate-500">{subtitle}</p>
        )}
      </div>
    </div>
  );
}
