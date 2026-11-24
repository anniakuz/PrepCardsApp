import { useEffect, useState } from "react";
import api, { errorText } from "../api.js";
import { useAuth } from "../auth.jsx";
import StatsPanel from "../components/StatsPanel.jsx";

function Percent({ value }) {
  return value === null || value === undefined ? <span className="text-slate-400">Sin datos</span> : <span>{value}%</span>;
}

function StudentDetail({ enrollment }) {
  const [stats, setStats] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.get(`/enrollments/${enrollment}/stats/`), api.get(`/enrollments/${enrollment}/reviews/`)])
      .then(([s, r]) => {
        setStats(s.data);
        setReviews(r.data);
      })
      .catch((err) => setError(errorText(err)));
  }, [enrollment]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!stats) return <p className="text-sm text-slate-500">Cargando</p>;
  return (
    <div className="space-y-5 border-t border-slate-200 pt-4">
      <StatsPanel stats={stats} />
      <div className="space-y-2">
        <h3 className="font-semibold">Últimas respuestas</h3>
        {reviews.length === 0 && <p className="text-sm text-slate-500">Todavía no ha respondido preguntas.</p>}
        {reviews.map((r, i) => (
          <div key={i} className="rounded-xl border border-slate-200 p-3 text-sm">
            <p className="font-medium">{r.question}</p>
            <p className={r.is_correct ? "text-green-700" : "text-red-600"}>
              {r.is_correct ? "Acertó" : "Falló"} con: {r.answer || "sin respuesta"}
              <span className="ml-2 text-slate-400">{new Date(r.created_at).toLocaleDateString()}</span>
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function StudentRow({ student }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="font-semibold">{student.username}</p>
        {student.shares_stats ? (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="badge">{student.answers} respuestas</span>
            <span className="badge">Aciertos <Percent value={student.accuracy} /></span>
            <button className="btn-secondary !py-1" onClick={() => setOpen(!open)}>{open ? "Ocultar detalle" : "Ver todo el detalle"}</button>
          </div>
        ) : (
          <span className="text-sm text-slate-500">No ha compartido sus datos contigo</span>
        )}
      </div>
      {open && <StudentDetail enrollment={student.enrollment} />}
    </div>
  );
}

function MentorStats() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/mentors/stats/").then(({ data }) => setData(data)).catch((err) => setError(errorText(err)));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-slate-500">Cargando</p>;
  return (
    <div className="space-y-8">
      <div>
        <h1 className="page-title">Estadísticas</h1>
        <p className="max-w-3xl text-sm text-slate-500">
          Cómo van tus cuestionarios y tus estudiantes. En los cuestionarios cuentan las respuestas de otros usuarios, no las tuyas.
          De cada estudiante ves todos sus datos, estadísticas por tema, evolución y respuestas, solo si decide compartirlos contigo.
        </p>
      </div>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Mis cuestionarios</h2>
        {data.quizzes.length === 0 && <p className="card text-sm text-slate-500">Todavía no has creado cuestionarios. Crea el primero desde Crear mi cuestionario.</p>}
        <div className="grid gap-4 sm:grid-cols-2">
          {data.quizzes.map((q) => (
            <div key={q.id} className="card space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold">{q.name}</p>
                <span className="badge">{q.visibility === "public" ? "Público" : "Privado"}</span>
              </div>
              <p className="text-sm text-slate-500">{q.question_count} preguntas</p>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl bg-slate-50 p-2"><p className="text-xl font-bold">{q.learners}</p><p className="text-xs text-slate-500">Alumnos</p></div>
                <div className="rounded-xl bg-slate-50 p-2"><p className="text-xl font-bold">{q.answers}</p><p className="text-xs text-slate-500">Respuestas</p></div>
                <div className="rounded-xl bg-slate-50 p-2"><p className="text-xl font-bold"><Percent value={q.accuracy} /></p><p className="text-xs text-slate-500">Aciertos</p></div>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Mis estudiantes</h2>
        {data.students.length === 0 && <p className="card text-sm text-slate-500">Todavía no tienes estudiantes activos.</p>}
        {data.students.map((s) => <StudentRow key={s.enrollment} student={s} />)}
      </section>
    </div>
  );
}

export default function Stats() {
  const { user } = useAuth();
  return user.role === "mentor" ? <MentorStats /> : <StudentStats />;
}

function StudentStats() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/stats/").then(({ data }) => setStats(data)).catch((err) => setError(errorText(err)));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!stats) return <p className="text-slate-500">Cargando</p>;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Estadísticas</h1>
        <p className="max-w-3xl text-sm text-slate-500">El nivel que has conseguido en cada tema o aptitud, por ejemplo Java avanzado o AWS básico, y cómo ha evolucionado. Sube con cinco aciertos seguidos y baja con tres fallos seguidos. Los cuestionarios de oferta no cuentan aquí, tienen su propio resultado.</p>
      </div>
      <StatsPanel stats={stats} />
    </div>
  );
}
