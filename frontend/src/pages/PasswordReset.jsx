import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import PasswordRules, { passwordIsValid } from "../components/PasswordRules.jsx";
import api, { errorText } from "../api.js";

function Shell({ title, children }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="card w-full max-w-sm space-y-4">
        <h1 className="text-xl font-bold text-indigo-700">{title}</h1>
        {children}
        <p className="text-center text-sm">
          <Link className="font-medium text-indigo-600" to="/login">Volver a entrar</Link>
        </p>
      </div>
    </div>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const { data } = await api.post("/auth/password-reset/", { email });
      setMessage(data.detail);
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <Shell title="Recuperar contraseña">
      {message ? (
        <p className="text-sm text-green-700">{message}</p>
      ) : (
        <form onSubmit={submit} className="space-y-3">
          <input
            className="input"
            type="email"
            placeholder="Tu email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button className="btn w-full">Enviar enlace</button>
        </form>
      )}
    </Shell>
  );
}

export function ResetPassword() {
  const { uid, token } = useParams();
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/auth/password-reset/confirm/", { uid, token, password });
      setDone(true);
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <Shell title="Nueva contraseña">
      {done ? (
        <p className="text-sm text-green-700">Contraseña cambiada. Ya puedes entrar.</p>
      ) : (
        <form onSubmit={submit} className="space-y-3">
          <input
            className="input"
            type="password"
            placeholder="Contraseña nueva"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <PasswordRules password={password} />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button className="btn w-full" disabled={!passwordIsValid(password)}>Cambiar contraseña</button>
        </form>
      )}
    </Shell>
  );
}
