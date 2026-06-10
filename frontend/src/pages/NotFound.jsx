import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="grid min-h-[60vh] place-items-center text-center">
      <div>
        <p className="text-6xl font-extrabold text-brand-500">404</p>
        <p className="mt-2 text-lg font-semibold">Página no encontrada</p>
        <Link to="/" className="btn-primary mt-4">
          Volver al inicio
        </Link>
      </div>
    </div>
  );
}
