import { useEffect, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import api, { errorText } from "../api.js";
import { useAuth } from "../auth.jsx";
import Chat from "../components/Chat.jsx";
import StatsPanel from "../components/StatsPanel.jsx";

export default function MentorChat() {
  const { id } = useParams();
  const { user } = useAuth();
  const { refreshNotes } = useOutletContext();
  const [enrollment, setEnrollment] = useState(null);
  const [ownTopics, setOwnTopics] = useState([]);
  const [view, setView] = useState(null);
  const [stats, setStats] = useState(null);
  const [reviews, setReviews] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/enrollments/")
      .then(({ data }) => {
        const found = data.find((e) => String(e.id) === id);
        if (!found) setError("Mentoría no encontrada");
        setEnrollment(found || null);
      })
      .catch((err) => setError(errorText(err)));
  }, [id]);

  useEffect(() => {
    if (enrollment?.as_role === "mentor") {
      api.get("/topics/mine/").then(({ data }) => setOwnTopics(data.filter((t) => t.mine && t.question_count > 0)));
    }
  }, [enrollment]);

  async function show(kind) {
    setView(view === kind ? null : kind);
    setError("");
    if (view === kind) return;
    try {
      const { data } = await api.get(`/enrollments/${id}/${kind}/`);
      if (kind === "stats") setStats(data);
      else setReviews(data);
    } catch (err) {
      setError(errorText(err));
      setView(null);
    }
  }

  if (!enrollment) return error ? <p className="text-red-600">{error}</p> : <p className="text-slate-500">Cargando</p>;
  const isMentor = enrollment.as_role === "mentor";
  const other = isMentor ? enrollment.student : enrollment.mentor;

  return (
    <div className="space-y-4">
      <div>
        <Link to="/mentoring" className="text-sm text-indigo-600">Volver a mentoría</Link>
        <h1 className="page-title">{isMentor ? "Estudiante" : "Mentor"}. {other.username}</h1>
      </div>
      {isMentor && (
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" onClick={() => show("stats")}>Ver estadísticas</button>
          <button className="btn-secondary" onClick={() => show("reviews")}>Ver respuestas</button>
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {view === "stats" && stats && <StatsPanel stats={stats} />}
      {view === "reviews" && reviews && (
        <div className="card space-y-2 text-sm">
          {reviews.length === 0 && <p className="text-slate-500">Todavía no hay respuestas.</p>}
          {reviews.map((r, i) => (
            <p key={i} className={r.is_correct ? "text-green-700" : "text-red-600"}>
              {r.is_correct ? "✓" : "✗"} {r.question} <span className="text-slate-500">→ {r.answer}</span>
            </p>
          ))}
        </div>
      )}
      {enrollment.status === "active" ? (
        <Chat enrollmentId={enrollment.id} ownTopics={ownTopics} onRead={refreshNotes} />
      ) : (
        <p className="card text-sm text-slate-600">Esta mentoría no está activa.</p>
      )}
      {!isMentor && <p className="text-xs text-slate-400">Conectado como {user.username}</p>}
    </div>
  );
}
