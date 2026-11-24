import { useEffect, useState } from "react";
import api, { errorText } from "../api.js";
import Assistant from "./Assistant.jsx";

/** Acciones de una pregunta. Guardar, preguntar al chatbot y enviarla a un mentor. */
export default function QuestionTools({ question, canSave = true }) {
  const [saved, setSaved] = useState(question.saved);
  const [panel, setPanel] = useState(null);
  const [mentors, setMentors] = useState(null);
  const [mentorId, setMentorId] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState({ text: "", error: false });

  useEffect(() => {
    setSaved(question.saved);
    setPanel(null);
    setMessage({ text: "", error: false });
  }, [question.id]);

  async function toggleSave() {
    try {
      if (saved) await api.delete(`/saved/${question.id}/`);
      else await api.post("/saved/", { question: question.id });
      setSaved(!saved);
    } catch (err) {
      setMessage({ text: errorText(err), error: true });
    }
  }

  async function openMentors() {
    setPanel(panel === "mentor" ? null : "mentor");
    if (mentors === null) {
      const { data } = await api.get("/enrollments/");
      const active = data.filter((e) => e.status === "active" && e.as_role === "student");
      setMentors(active);
      if (active.length) setMentorId(String(active[0].id));
    }
  }

  async function sendToMentor(event) {
    event.preventDefault();
    try {
      await api.post(`/enrollments/${mentorId}/messages/`, { question: question.id, text: note });
      setMessage({ text: "Pregunta enviada al chat del mentor", error: false });
      setPanel(null);
      setNote("");
    } catch (err) {
      setMessage({ text: errorText(err), error: true });
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {canSave && <button className="btn-secondary" onClick={toggleSave}>{saved ? "Quitar de guardadas" : "Guardar pregunta"}</button>}
        <button className="btn-secondary" onClick={() => setPanel(panel === "bot" ? null : "bot")}>Preguntar al chatbot</button>
        <button className="btn-secondary" onClick={openMentors}>Enviar a mi mentor</button>
      </div>
      {message.text && <p className={`text-sm ${message.error ? "text-red-600" : "text-green-700"}`}>{message.text}</p>}
      {panel === "bot" && <Assistant questionId={question.id} onClose={() => setPanel(null)} />}
      {panel === "mentor" && (
        <form onSubmit={sendToMentor} className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-4">
          {mentors && mentors.length === 0 ? (
            <p className="text-sm text-slate-600">Todavía no tienes mentores. Pide uno desde la sección Mentoría.</p>
          ) : (
            <>
              <select className="input" value={mentorId} onChange={(e) => setMentorId(e.target.value)}>
                {(mentors || []).map((e) => <option key={e.id} value={e.id}>{e.mentor.username}</option>)}
              </select>
              <input className="input" placeholder="Mensaje (opcional)" value={note} onChange={(e) => setNote(e.target.value)} />
              <button className="btn" disabled={!mentorId}>Enviar</button>
            </>
          )}
        </form>
      )}
    </div>
  );
}
