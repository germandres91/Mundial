import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import ThemeToggle from "../components/ThemeToggle";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err?.response?.status === 401
          ? "Correo o contraseña incorrectos."
          : "No se pudo iniciar sesión. Intenta de nuevo."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-700 via-brand-600 to-brand-900 p-4">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <div className="w-full max-w-md">
        <div className="mb-6 text-center text-white">
          <div className="text-5xl">🏟️</div>
          <h1 className="mt-2 text-3xl font-extrabold">Mundial 2026</h1>
          <p className="text-sm text-brand-100">
            Plataforma de predicciones · USA · Canadá · México
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="space-y-4 rounded-3xl border border-white/20 bg-white/95 p-6 shadow-2xl backdrop-blur dark:bg-slate-900/95"
        >
          <div>
            <h2 className="text-lg font-bold">Iniciar sesión</h2>
            <p className="text-sm text-slate-500">
              Ingresa con el usuario que te compartieron.
            </p>
          </div>

          {error && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-500">
              {error}
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">
              Correo electrónico
            </label>
            <input
              type="email"
              autoComplete="username"
              className="input"
              placeholder="tucorreo@ejemplo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">
              Contraseña
            </label>
            <input
              type="password"
              autoComplete="current-password"
              className="input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Ingresando…" : "Ingresar"}
          </button>

          <p className="text-center text-xs text-slate-400">
            ¿No tienes usuario? Solicítalo al administrador.
          </p>
        </form>
      </div>
    </div>
  );
}
