import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import ThemeToggle from "../components/ThemeToggle";

const NAV = [
  { to: "/", label: "Inicio Mundial", icon: "🏟️", end: true },
  { to: "/partidos", label: "Partidos", icon: "⚽" },
  { to: "/predicciones", label: "Predicciones", icon: "🎯" },
  { to: "/ranking", label: "Ranking", icon: "🏆" },
  { to: "/estadisticas", label: "Estadísticas", icon: "📊" },
  { to: "/participante", label: "Participantes", icon: "👤" },
  { to: "/admin", label: "Administración", icon: "⚙️" },
];

export default function MainLayout() {
  const [open, setOpen] = useState(false);
  const items = NAV;

  return (
    <div className="min-h-screen lg:flex">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform border-r border-slate-200 bg-white p-4 transition-transform dark:border-slate-800 dark:bg-slate-900 lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-8 flex items-center gap-2 px-2">
          <span className="text-2xl">🌍</span>
          <div>
            <p className="font-extrabold leading-tight">Mundial 2026</p>
            <p className="text-xs text-slate-500">Predicciones</p>
          </div>
        </div>
        <nav className="space-y-1">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-600 text-white shadow"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
          <button
            className="btn-ghost px-3 py-2 lg:hidden"
            onClick={() => setOpen(true)}
            aria-label="Menú"
          >
            ☰
          </button>
          <div className="hidden text-sm text-slate-500 lg:block">
            Plataforma de predicciones · Copa del Mundo 2026 🇺🇸🇨🇦🇲🇽
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </header>

        <main className="flex-1 p-4 lg:p-8">
          <Outlet />
        </main>

        <footer className="border-t border-slate-200 px-4 py-4 text-center text-xs text-slate-500 dark:border-slate-800">
          Mundial 2026 Predictions · {new Date().getFullYear()}
        </footer>
      </div>
    </div>
  );
}
