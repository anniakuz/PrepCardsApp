import { useEffect, useRef, useState } from "react";
import api, { errorText } from "../api.js";

/** Chatbot con Claude para dudas de una pregunta. Tiene límite diario de mensajes. */
export default function Assistant({ questionId, onClose }) {
  const [messages, setMessages] = useState([]);
  const [usage, setUsage] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef(null);

  useEffect(() => {
    setMessages([]);
    api
      .get(`/questions/${questionId}/assistant/`)
      .then(({ data }) => {
        setMessages(data.messages);
        setUsage(data);
      })
      .catch((err) => setError(errorText(err)));
  }, [questionId]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "nearest" });
  }, [messages, busy]);

  async function send(event) {
    event.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    setBusy(true);
    setError("");
    setMessages((current) => [...current, { id: `tmp-${Date.now()}`, role: "user", text: value }]);
    setText("");
    try {
      const { data } = await api.post(`/questions/${questionId}/assistant/`, { text: value });
      setMessages((current) => [...current, data.message]);
      setUsage(data);
    } catch (err) {
      setError(errorText(err));
      setMessages((current) => current.slice(0, -1));
      setText(value);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 rounded-xl border border-indigo-200 bg-indigo-50/40 p-4">
      <div className="flex items-center justify-between text-sm">
        <span className="font-semibold text-indigo-700">Chatbot</span>
        <div className="flex items-center gap-3 text-slate-500">
          {usage && <span title={`Límite ${usage.limit} al día y ${usage.weekly_limit} a la semana`}>Hoy {usage.remaining_today}/{usage.limit} · Semana {usage.remaining_week}/{usage.weekly_limit}</span>}
          {onClose && <button onClick={onClose} className="text-slate-500 hover:text-slate-800">Cerrar</button>}
        </div>
      </div>
      <div className="max-h-72 space-y-2 overflow-y-auto">
        {messages.length === 0 && <p className="text-sm text-slate-500">Pregunta lo que no entiendas de esta pregunta.</p>}
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            <p
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
                message.role === "user" ? "bg-indigo-600 text-white" : "bg-white text-slate-800 shadow-sm"
              }`}
            >
              {message.text}
            </p>
          </div>
        ))}
        {busy && <p className="text-sm text-slate-400">Escribiendo</p>}
        <div ref={bottom} />
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <form onSubmit={send} className="flex gap-2">
        <input className="input" placeholder="Escribe tu duda" value={text} maxLength={1000} onChange={(e) => setText(e.target.value)} />
        <button className="btn" disabled={busy || !text.trim()}>Enviar</button>
      </form>
    </div>
  );
}
