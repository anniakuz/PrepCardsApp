import { useState } from "react";
import { Link } from "react-router-dom";

const KEY = "cookie_notice";

function seen() {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

/** Aviso de cookies. Solo se usa almacenamiento técnico, así que no hay nada que rechazar. */
export default function CookieNotice() {
  const [hidden, setHidden] = useState(seen());
  if (hidden) return null;

  function accept() {
    try {
      localStorage.setItem(KEY, "1");
    } catch {
      // sin almacenamiento se vuelve a mostrar en la siguiente visita
    }
    setHidden(true);
  }

  return (
    <div role="dialog" aria-label="Aviso de cookies" className="fixed inset-x-0 bottom-0 z-50 border-t border-slate-200 bg-white p-4 shadow-lg">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
        <p className="flex-1">
          Usamos solo almacenamiento técnico necesario para mantener tu sesión. No usamos cookies de publicidad ni de analítica.{" "}
          <Link to="/legal/cookies" className="font-medium text-indigo-600">Más información</Link>
        </p>
        <button className="btn" onClick={accept}>Aceptar</button>
      </div>
    </div>
  );
}
