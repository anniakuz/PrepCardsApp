import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api, { chatSocketUrl, errorText } from "../api.js";
import { useAuth } from "../auth.jsx";

const QUESTION_LINK = /\S*[?&]question=(\d+)\S*/;

/**
 * Chat en tiempo real entre estudiante y mentor.
 * El historial se carga por REST y los mensajes nuevos llegan por WebSocket.
 * Si el socket no está abierto, el envío cae a REST.
 */
export default function Chat({ enrollmentId, ownTopics = [], onRead }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [topic, setTopic] = useState("");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const socket = useRef(null);
  const bottom = useRef(null);

  const append = (message) =>
    setMessages((current) => (current.some((m) => m.id === message.id) ? current : [...current, message]));

  useEffect(() => {
    let closed = false;
    let retry = null;
    setMessages([]);
    api
      .get(`/enrollments/${enrollmentId}/messages/`)
      .then(({ data }) => {
        setMessages(data);
        onRead?.();
      })
      .catch((err) => setError(errorText(err)));

    function connect() {
      const ws = new WebSocket(chatSocketUrl(enrollmentId));
      socket.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.error) setError(data.error);
        else {
          append(data);
          if (data.sender !== user.id) api.post(`/enrollments/${enrollmentId}/read/`).then(() => onRead?.());
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (closed) return;
        // Renueva el token si ha caducado y vuelve a conectar.
        retry = setTimeout(() => api.get("/auth/me/").then(connect).catch(() => {}), 3000);
      };
    }
    connect();

    return () => {
      closed = true;
      clearTimeout(retry);
      socket.current?.close();
    };
  }, [enrollmentId]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "nearest" });
  }, [messages]);

  async function send(event) {
    event.preventDefault();
    const value = text.trim();
    if (!value && !topic) return;
    setError("");
    if (!topic && socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify({ text: value }));
    } else {
      try {
        const { data } = await api.post(`/enrollments/${enrollmentId}/messages/`, { text: value, topic: topic ? Number(topic) : undefined });
        append(data);
      } catch (err) {
        setError(errorText(err));
        return;
      }
    }
    setText("");
    setTopic("");
  }

  return (
    <div className="card flex h-[32rem] flex-col !p-0">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2 text-sm">
        <span className="font-semibold">Chat</span>
        <span className={connected ? "text-green-600" : "text-slate-400"}>
          {connected ? "En línea" : "Conectando"}
        </span>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 && <p className="text-center text-sm text-slate-400">Todavía no hay mensajes.</p>}
        {messages.map((message) => {
          const mine = message.sender === user.id;
          return (
            <div key={message.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] space-y-2 rounded-2xl px-3 py-2 text-sm ${
                  mine ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-800"
                }`}
              >
                {!mine && <p className="text-xs font-semibold opacity-70">{message.sender_name}</p>}
                {message.text && <p className="whitespace-pre-wrap">{message.text}</p>}
                {message.question && (
                  <Link to={`/question/${message.question.id}`} className="block rounded-lg bg-white p-2 text-slate-700 shadow-sm">
                    {message.question.level && <span className="badge">Nivel {message.question.level}</span>}
                    <span className="mt-1 block">{message.question.text}</span>
                    <span className="mt-1 block text-xs font-medium text-indigo-600">Abrir pregunta</span>
                  </Link>
                )}
                {message.topic && (
                  <Link to={`/practice/${message.topic.id}`} className="block rounded-lg bg-white p-2 text-slate-700 shadow-sm">
                    <span className="block font-semibold">Tema privado. {message.topic.name}</span>
                    <span className="mt-1 block text-xs font-medium text-indigo-600">Practicar tema</span>
                  </Link>
                )}
                <p className="text-right text-[10px] opacity-60">
                  {new Date(message.created_at).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" })}
                </p>
              </div>
            </div>
          );
        })}
        <div ref={bottom} />
      </div>

      <form onSubmit={send} className="space-y-2 border-t border-slate-200 p-3">
        {error && <p className="text-xs text-red-600">{error}</p>}
        <div className="flex gap-2">
          <input
            className="input"
            placeholder="Escribe un mensaje"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          {ownTopics.length > 0 && (
            <select className="input !w-48" value={topic} onChange={(e) => setTopic(e.target.value)}>
              <option value="">Sin tema</option>
              {ownTopics.map((t) => <option key={t.id} value={t.id}>Enviar tema. {t.name}</option>)}
            </select>
          )}
          <button className="btn">Enviar</button>
        </div>
      </form>
    </div>
  );
}
