import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { EXPERIENCE_OPTIONS, SEX_OPTIONS, errorText } from "../api.js";
import PasswordRules, { passwordIsValid } from "../components/PasswordRules.jsx";
import { useAuth } from "../auth.jsx";

const EMPTY = { first_name: "", last_name: "", username: "", email: "", password: "", repeat: "", age: "", role: "student", sex: "undisclosed", experience: "none", about: "", accept_terms: false };

export default function AuthPage({ mode }) {
  const isRegister = mode === "register";
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;
  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (isRegister && !passwordIsValid(form.password)) return setError("La contraseña no cumple los requisitos");
    if (isRegister && form.password !== form.repeat) return setError("Las contraseñas no coinciden");
    setBusy(true);
    try {
      if (isRegister) await register({ ...form, age: Number(form.age) });
      else await login(form.username, form.password);
      navigate(isRegister ? (form.role === "mentor" ? "/mentoring" : "/topics") : "/");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-500 px-4 py-8">
      <form onSubmit={submit} className="card w-full max-w-md space-y-4 shadow-2xl">
        <div>
          <h1 className="page-title">PrepCards</h1>
          <p className="text-sm text-slate-500">
            {isRegister ? "Crea tu cuenta" : "Practica preguntas de entrevista técnica"}
          </p>
        </div>
        {isRegister && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input className="input" placeholder="Nombre" autoComplete="given-name" maxLength={60} value={form.first_name} onChange={update("first_name")} required />
            <input className="input" placeholder="Apellidos" autoComplete="family-name" maxLength={100} value={form.last_name} onChange={update("last_name")} required />
          </div>
        )}
        <input className="input" placeholder="Usuario" value={form.username} onChange={update("username")} required />
        {isRegister && (
          <input className="input" type="email" placeholder="Email" value={form.email} onChange={update("email")} required />
        )}
        <input className="input" type="password" placeholder="Contraseña" autoComplete={isRegister ? "new-password" : "current-password"} value={form.password} onChange={update("password")} required />
        {isRegister && (
          <>
            <input
              className={`input ${form.repeat && (form.repeat === form.password ? "!border-green-500" : "!border-red-400")}`}
              type="password"
              placeholder="Repite la contraseña"
              autoComplete="new-password"
              value={form.repeat}
              onChange={update("repeat")}
              required
            />
            {form.repeat && (
              <p className={`text-sm ${form.repeat === form.password ? "text-green-700" : "text-red-600"}`}>
                {form.repeat === form.password ? "Las contraseñas coinciden" : "Las contraseñas no coinciden"}
              </p>
            )}
            <PasswordRules password={form.password} />
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {[["student", "Soy estudiante", "Quiero practicar"], ["mentor", "Soy mentor", "Quiero ayudar a otros"]].map(([value, title, hint]) => (
                <button
                  type="button"
                  key={value}
                  onClick={() => setForm({ ...form, role: value })}
                  className={`rounded-xl border p-3 text-left text-sm transition ${
                    form.role === value ? "border-indigo-600 bg-indigo-50 ring-2 ring-indigo-200" : "border-slate-300 bg-white hover:border-indigo-400"
                  }`}
                >
                  <span className="block font-semibold">{title}</span>
                  <span className="text-xs text-slate-500">{hint}</span>
                </button>
              ))}
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="text-sm">
                <span className="mb-1 block text-slate-500">Edad</span>
                <input className="input" type="number" min="14" max="100" value={form.age} onChange={update("age")} required />
              </label>
              <label className="text-sm">
                <span className="mb-1 block text-slate-500">Sexo</span>
                <select className="input" value={form.sex} onChange={update("sex")}>
                  {SEX_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
            </div>
            <label className="block text-sm">
              <span className="mb-1 block text-slate-500">Experiencia programando</span>
              <select className="input" value={form.experience} onChange={update("experience")}>
                {EXPERIENCE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-slate-500">
                {form.role === "mentor" ? "Descripción como mentor (obligatoria, entre 20 y 100 caracteres)" : "Sobre mí (opcional, máximo 100 caracteres, lo ven otros usuarios)"}
              </span>
              <textarea
                className="input h-20 resize-none"
                maxLength={100}
                value={form.about}
                onChange={update("about")}
                required={form.role === "mentor"}
                minLength={form.role === "mentor" ? 20 : undefined}
                placeholder={form.role === "mentor" ? "Tu experiencia, las tecnologías que dominas y cómo ayudas a preparar entrevistas" : ""}
              />
            </label>
          </>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {isRegister && (
          <div className="space-y-3">
          <p className="rounded-xl bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800">Esta plataforma es solo para mayores de 14 años.</p>
          <label className="flex items-start gap-2 text-sm text-slate-600">
            <input type="checkbox" className="mt-1" checked={form.accept_terms} onChange={(e) => setForm({ ...form, accept_terms: e.target.checked })} />
            <span>
              He leído y acepto los <Link className="font-medium text-indigo-600" to="/legal/terminos" target="_blank">términos de uso</Link> y
              la <Link className="font-medium text-indigo-600" to="/legal/privacidad" target="_blank">política de privacidad</Link>.
            </span>
          </label>
          </div>
        )}
        <button className="btn w-full" disabled={busy || (isRegister && !form.accept_terms)}>{isRegister ? "Registrarme" : "Entrar"}</button>
        {!isRegister && (
          <p className="text-center text-sm">
            <Link className="text-slate-500 hover:text-indigo-600" to="/forgot">He olvidado mi contraseña</Link>
          </p>
        )}
        <p className="text-center text-sm text-slate-500">
          {isRegister ? "¿Ya tienes cuenta? " : "¿No tienes cuenta? "}
          <Link className="font-medium text-indigo-600" to={isRegister ? "/login" : "/register"}>
            {isRegister ? "Entrar" : "Regístrate"}
          </Link>
        </p>
      </form>
    </div>
  );
}
