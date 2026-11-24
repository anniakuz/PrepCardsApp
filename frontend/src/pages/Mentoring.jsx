import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import api, { errorText } from "../api.js";
import { useAuth } from "../auth.jsx";

const STATUS = { pending: "Pendiente", active: "Activa", rejected: "Rechazada", ended: "Terminada" };
const DEFAULT_MESSAGE = "Hola, quiero que seas mi mentor";

function Unread({ count }) {
  return count ? <span className="ml-2 rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold text-white">{count} nuevos</span> : null;
}

function MyMentors({ items, reload, unread }) {
  const [editing, setEditing] = useState(null);
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  async function call(promise) {
    setError("");
    try {
      await promise;
      setEditing(null);
      reload();
    } catch (err) {
      setError(errorText(err));
    }
  }

  if (items.length === 0) return <p className="card text-sm text-slate-500">Todavía no tienes mentores. Pide uno de la lista de abajo.</p>;
  return (
    <div className="space-y-3">
      {error && <p className="text-sm text-red-600">{error}</p>}
      {items.map((e) => (
        <div key={e.id} className="card space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-semibold">{e.mentor.username} <span className="badge ml-2">{STATUS[e.status]}</span></p>
            <div className="flex gap-2">
              {e.status === "active" && <Link to={`/mentoring/${e.id}`} className="btn">Abrir chat<Unread count={unread[e.id]} /></Link>}
              {["pending", "active"].includes(e.status) && (
                <button className="btn-secondary" onClick={() => window.confirm("¿Terminar esta mentoría?") && call(api.post(`/enrollments/${e.id}/end/`))}>
                  {e.status === "pending" ? "Cancelar" : "Terminar"}
                </button>
              )}
            </div>
          </div>
          {e.status === "pending" &&
            (editing === e.id ? (
              <div className="flex gap-2">
                <input className="input" value={text} maxLength={500} onChange={(ev) => setText(ev.target.value)} />
                <button className="btn" onClick={() => call(api.patch(`/enrollments/${e.id}/`, { request_message: text }))}>Guardar</button>
              </div>
            ) : (
              <p className="text-sm text-slate-600">
                “{e.request_message}”{" "}
                <button className="font-medium text-indigo-600" onClick={() => { setEditing(e.id); setText(e.request_message); }}>Editar mensaje</button>
              </p>
            ))}
          {e.status === "active" && (
            <div className="flex flex-wrap gap-4 text-sm text-slate-600">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={e.share_data} onChange={(ev) => call(api.patch(`/enrollments/${e.id}/`, { share_data: ev.target.checked }))} />
                Compartir mis estadísticas y respuestas con este mentor
              </label>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function MentorList({ reload }) {
  const [mentors, setMentors] = useState([]);
  const [open, setOpen] = useState(null);
  const [message, setMessage] = useState(DEFAULT_MESSAGE);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/mentors/", { params: { q: search } }).then(({ data }) => setMentors(data));
  }, [search, reload]);

  async function request(mentor) {
    setError("");
    try {
      await api.post("/enrollments/", { mentor: mentor.id, message });
      setOpen(null);
      setMessage(DEFAULT_MESSAGE);
      reload();
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <div className="space-y-3">
      <input className="input max-w-md" placeholder="Buscar por nombre o tecnología, por ejemplo Java o React" value={search} onChange={(e) => setSearch(e.target.value)} />
      {error && <p className="text-sm text-red-600">{error}</p>}
      {mentors.length === 0 && <p className="card text-sm text-slate-500">No hay mentores disponibles ahora.</p>}
      {mentors.map((mentor) => (
        <div key={mentor.id} className="card space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="font-semibold">{mentor.username}</p>
              <p className="mt-1 max-w-2xl text-sm text-slate-600">{mentor.about || "Este mentor todavía no ha escrito su descripción."}</p>
              {mentor.technologies?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {mentor.technologies.map((t) => <span key={t} className="badge">{t}</span>)}
                </div>
              )}
            </div>
            <button className="btn" onClick={() => setOpen(open === mentor.id ? null : mentor.id)}>Pedir mentoría</button>
          </div>
          {open === mentor.id && (
            <div className="flex gap-2">
              <input className="input" value={message} maxLength={500} onChange={(e) => setMessage(e.target.value)} />
              <button className="btn" onClick={() => request(mentor)} disabled={!message.trim()}>Enviar solicitud</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function MentorPanel({ items, reload, unread, pendingCount }) {
  const { user, setUser } = useAuth();
  const [error, setError] = useState("");

  async function call(promise) {
    setError("");
    try {
      await promise;
      reload();
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function toggleAvailability(value) {
    try {
      const { data } = await api.put("/mentors/availability/", { accepting_requests: value });
      setUser({ ...user, accepting_requests: data.accepting_requests });
    } catch (err) {
      setError(errorText(err));
    }
  }

  const pending = items.filter((e) => e.status === "pending");
  const active = items.filter((e) => e.status === "active");
  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">Como mentor</h2>
      <label className="card flex items-center gap-3 text-sm">
        <input type="checkbox" checked={user.accepting_requests} onChange={(e) => toggleAvailability(e.target.checked)} />
        <span>Estoy disponible para recibir solicitudes nuevas</span>
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <h3 className="font-medium">Solicitudes recibidas{pendingCount > 0 && <span className="ml-2 rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold text-white">{pendingCount}</span>}</h3>
      {pending.length === 0 && <p className="card text-sm text-slate-500">No tienes solicitudes pendientes.</p>}
      {pending.map((e) => (
        <div key={e.id} className="card flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold">{e.student.username}</p>
            <p className="text-sm text-slate-600">“{e.request_message}”</p>
          </div>
          <div className="flex gap-2">
            <button className="btn" onClick={() => call(api.post(`/enrollments/${e.id}/accept/`))}>Aceptar</button>
            <button className="btn-secondary" onClick={() => call(api.post(`/enrollments/${e.id}/reject/`))}>Rechazar</button>
          </div>
        </div>
      ))}
      <h3 className="font-medium">Mis estudiantes</h3>
      {active.length === 0 && <p className="card text-sm text-slate-500">Todavía no tienes estudiantes.</p>}
      {active.map((e) => (
        <div key={e.id} className="card flex flex-wrap items-center justify-between gap-3">
          <p className="font-semibold">{e.student.username}</p>
          <div className="flex gap-2">
            <Link to={`/mentoring/${e.id}`} className="btn">Abrir chat<Unread count={unread[e.id]} /></Link>
            <button className="btn-secondary" onClick={() => window.confirm("¿Terminar esta mentoría?") && call(api.post(`/enrollments/${e.id}/end/`))}>Terminar</button>
          </div>
        </div>
      ))}
    </section>
  );
}

export default function Mentoring() {
  const { user } = useAuth();
  const { notes, refreshNotes } = useOutletContext();
  const [items, setItems] = useState([]);
  const [tick, setTick] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/enrollments/").then(({ data }) => setItems(data)).catch((err) => setError(errorText(err)));
  }, [tick]);
  const reload = () => {
    setTick((t) => t + 1);
    refreshNotes();
  };
  useEffect(() => {
    setTick((t) => t + 1);
  }, [notes.pending_requests]);

  if (user.role === "mentor") {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="page-title">Mis estudiantes</h1>
          <p className="max-w-3xl text-sm text-slate-500">
            Tu espacio como mentor. Acepta solicitudes, chatea con tus estudiantes, envíales tus cuestionarios y revisa su progreso en Estadísticas
            cuando comparten sus datos contigo. Los mentores no practican temas, tu trabajo está en acompañar a los estudiantes.
          </p>
        </div>
        {error && <p className="text-red-600">{error}</p>}
        <MentorPanel items={items.filter((e) => e.as_role === "mentor")} reload={reload} unread={notes.unread} pendingCount={notes.pending_requests} />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="page-title">Mentoría</h1>
        <p className="text-sm text-slate-500">Los mentores son personas con experiencia que resuelven tus dudas y te ayudan a preparar entrevistas. Lee su descripción, elige el que mejor encaje y pide mentoría. El chat se abre cuando acepta tu solicitud y podrás enviarle preguntas concretas desde la práctica.</p>
      </div>
      {error && <p className="text-red-600">{error}</p>}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Mis mentores</h2>
        <MyMentors items={items.filter((e) => e.as_role === "student")} reload={reload} unread={notes.unread} />
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Otros mentores disponibles</h2>
        <MentorList reload={reload} />
      </section>
    </div>
  );
}
