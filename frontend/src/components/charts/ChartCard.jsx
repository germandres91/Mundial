export default function ChartCard({ title, subtitle, children, bodyClassName = "h-72" }) {
  return (
    <div className="card animate-fade-in">
      <div className="mb-4">
        <h3 className="font-semibold">{title}</h3>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
      <div className={`${bodyClassName} w-full`}>{children}</div>
    </div>
  );
}
