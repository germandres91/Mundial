export default function ChartCard({ title, subtitle, children }) {
  return (
    <div className="card animate-fade-in">
      <div className="mb-4">
        <h3 className="font-semibold">{title}</h3>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
      <div className="h-72 w-full">{children}</div>
    </div>
  );
}
