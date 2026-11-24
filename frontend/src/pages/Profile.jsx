import { useState } from "react";
import { Link } from "react-router-dom";
import PasswordRules from "../components/PasswordRules.jsx";
import api, { EXPERIENCE_OPTIONS, ROLE_LABELS, SEX_OPTIONS, errorText } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function Profile() {
  const { user, setUser, logout } = useAuth();
  const [deletePassword, setDeletePassword] = useState("");
  const [privacyInfo, setPrivacyInfo] = useState("");
  const [form, setForm] = useState({
    first_name: user.first_name, last_name: user.last_name, email: user.email, age: user.age ?? "", sex: user.sex, experience: user.experience, about: user.about,
  });
  const [password, setPassword] = useState({ old_password: "", new_password: "" });
  const [info, setInfo] = useState({ text: "", error: false });
  const [passInfo, setPassInfo] = useState({ text: "", error: false });
  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  async function save(event) {
    event.preventDefault();
    try {
      const { data } = await api.patch("/auth/me/", { ...form, age: Number(form.age) });
      setUser(data);
      setInfo({ text: "Datos guardados", error: false });
    } catch (err) {
      setInfo({ text: errorText(err), error: true });
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    try {
      await api.post("/auth/change-password/", password);
      setPassword({ old_password: "", new_password: "" });
      setPassInfo({ text: "Contraseña cambiada", error: false });
    } catch (err) {
      setPassInfo({ text: errorText(err), error: true });
    }
  }

  async function exportData() {
    try {
      const { data } = await api.get("/auth/export/");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "mis-datos-prepcards.json";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setPrivacyInfo(errorText(err));
    }
  }

  async function deleteAccount(event) {
    event.preventDefault();
    if (!window.confirm("Se borrarán tu cuenta y todos tus datos. No se puede deshacer. ¿Continuar?")) return;
    try {
      await api.post("/auth/delete-account/", { password: deletePassword });
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      window.location.href = "/login";
    } catch (err) {
      setPrivacyInfo(errorText(err));
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="page-title">Mi perfil</h1>
        <p className="text-sm text-slate-500">{user.first_name} {user.last_name} · {user.username} · <span className="badge">{ROLE_LABELS[user.role]}</span></p>
        <p className="max-w-3xl text-sm text-slate-500">Mantén tus datos al día. Tu experiencia nos ayuda a proponerte temas y tu descripción es lo que ven los demás{user.role === "mentor" ? " cuando buscan mentor" : " en tu perfil"}.</p>
      </div>

      <form onSubmit={save} className="card max-w-xl space-y-4">
        <h2 className="text-lg font-semibold">Información sobre mí</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="text-sm">
            <span className="mb-1 block text-slate-500">Nombre</span>
            <input className="input" value={form.first_name} maxLength={60} onChange={update("first_name")} required />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-500">Apellidos</span>
            <input className="input" value={form.last_name} maxLength={100} onChange={update("last_name")} required />
          </label>
        </div>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-500">Email</span>
          <input className="input" type="email" value={form.email} onChange={update("email")} required />
        </label>
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
          <span className="mb-1 block text-slate-500">Experiencia</span>
          <select className="input" value={form.experience} onChange={update("experience")}>
            {EXPERIENCE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-500">Sobre mí ({(form.about || "").length}/100). Lo ven otros usuarios</span>
          <textarea className="input h-24 resize-none" required={user.role === "mentor"} minLength={user.role === "mentor" ? 20 : undefined} maxLength={100} value={form.about} onChange={update("about")} />
        </label>
        {info.text && <p className={`text-sm ${info.error ? "text-red-600" : "text-green-700"}`}>{info.text}</p>}
        <button className="btn">Guardar</button>
      </form>

      <form onSubmit={changePassword} className="card max-w-xl space-y-4">
        <h2 className="text-lg font-semibold">Cambiar contraseña</h2>
        <input className="input" type="password" placeholder="Contraseña actual" value={password.old_password} onChange={(e) => setPassword({ ...password, old_password: e.target.value })} required />
        <input className="input" type="password" placeholder="Contraseña nueva" value={password.new_password} onChange={(e) => setPassword({ ...password, new_password: e.target.value })} required />
        <PasswordRules password={password.new_password} />
        {passInfo.text && <p className={`text-sm ${passInfo.error ? "text-red-600" : "text-green-700"}`}>{passInfo.text}</p>}
        <button className="btn">Cambiar contraseña</button>
      </form>

      <div className="card max-w-xl space-y-4">
        <h2 className="text-lg font-semibold">Mis datos y privacidad</h2>
        <p className="text-sm text-slate-600">
          Puedes descargar tus datos o eliminar tu cuenta. Más información en la{" "}
          <Link className="font-medium text-indigo-600" to="/legal/privacidad">política de privacidad</Link>.
        </p>
        <button type="button" className="btn-secondary" onClick={exportData}>Descargar mis datos</button>
        <form onSubmit={deleteAccount} className="space-y-2 border-t border-slate-200 pt-4">
          <p className="text-sm font-medium text-red-700">Eliminar mi cuenta</p>
          <input className="input" type="password" placeholder="Tu contraseña" value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} required />
          <button className="btn !bg-red-600 hover:!bg-red-700">Eliminar cuenta y datos</button>
        </form>
        {privacyInfo && <p className="text-sm text-red-600">{privacyInfo}</p>}
      </div>
    </div>
  );
}
