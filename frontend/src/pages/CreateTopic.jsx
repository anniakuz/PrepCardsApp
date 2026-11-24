import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api, { downloadExample, errorText } from "../api.js";

const EXAMPLE = `{
  "questions": [
    {
      "level": 1,
      "text": "¿Qué palabra clave declara una constante en JavaScript?",
      "choices": ["var", "let", "const", "static"],
      "answer": 2,
      "explanation": "const no se puede reasignar."
    },
    {
      "level": 3,
      "text": "¿Qué devuelve typeof null?",
      "choices": ["null", "object", "undefined", "number"],
      "answer": 1,
      "explanation": "Es un error histórico del lenguaje."
    }
  ]
}`;

function FormatExample() {
  return (
    <aside className="card space-y-3 lg:sticky lg:top-24 lg:self-start">
      <h2 className="text-lg font-semibold">Formato del archivo JSON</h2>
      <pre className="max-h-96 overflow-auto rounded-xl bg-slate-900 p-4 text-xs leading-relaxed text-slate-100">{EXAMPLE}</pre>
      <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
        <li><b>text</b>. El enunciado de la pregunta.</li>
        <li><b>choices</b>. Exactamente 4 opciones distintas.</li>
        <li><b>answer</b>. Posición de la correcta, empezando en 0. En el ejemplo, 2 es const.</li>
        <li><b>level</b>. Del 1 (inicial) al 5 (experto). Opcional, pero si lo pones, ponlo en todas.</li>
        <li><b>explanation</b>. Opcional. Por qué es correcta.</li>
        <li>Mínimo 20 preguntas. El ejemplo solo muestra 2.</li>
      </ul>
      <button type="button" className="btn-secondary w-full" onClick={() => downloadExample()}>Descargar archivo de ejemplo</button>
    </aside>
  );
}

const PUBLISH = { pending: "Verificando con IA", approved: "Publicado", rejected: "Rechazado por la verificación", error: "No se pudo verificar" };

function ErrorList({ error }) {
  if (!error) return null;
  return Array.isArray(error) ? (
    <ul className="list-disc space-y-1 pl-5 text-sm text-red-600">{error.map((e, i) => <li key={i}>{e}</li>)}</ul>
  ) : (
    <p className="text-sm text-red-600">{error}</p>
  );
}

function fileErrors(err) {
  const data = err.response?.data;
  if (data?.questions && Array.isArray(data.questions)) return data.questions;
  if (data?.file) return data.file;
  return errorText(err);
}

function MyCreated({ reloadKey, onChange }) {
  const [topics, setTopics] = useState([]);
  const [error, setError] = useState("");
  const [replacing, setReplacing] = useState(null);
  const input = useRef(null);

  function load() {
    api.get("/topics/mine/").then(({ data }) => setTopics(data.filter((t) => t.mine)));
  }
  useEffect(load, [reloadKey]);
  // La verificación con IA corre en Celery. Se consulta mientras haya temas verificándose.
  useEffect(() => {
    if (!topics.some((t) => t.publish_status === "pending")) return;
    const timer = setTimeout(load, 2500);
    return () => clearTimeout(timer);
  }, [topics]);

  async function run(promise) {
    setError("");
    try {
      await promise;
      load();
      onChange?.();
    } catch (err) {
      setError(fileErrors(err));
    }
  }

  function replaceFile(event) {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file || !replacing) return;
    const body = new FormData();
    body.append("file", file);
    run(api.put(`/topics/${replacing}/questions/`, body));
    setReplacing(null);
  }

  if (topics.length === 0) return null;
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Mis cuestionarios creados</h2>
      <input ref={input} type="file" accept=".json,application/json" className="hidden" onChange={replaceFile} />
      <ErrorList error={error} />
      {topics.map((topic) => (
        <div key={topic.id} className="card space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-semibold">{topic.name}</p>
              <p className="text-xs text-slate-500">{topic.question_count} preguntas · {topic.uses_levels ? "con niveles" : "sin niveles"}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="badge">{topic.visibility === "public" ? "Público" : "Privado"}</span>
              {topic.publish_status && <span className="badge">{PUBLISH[topic.publish_status]}</span>}
            </div>
          </div>
          {topic.publish_status === "error" && (
            <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
              La IA no ha podido verificar el cuestionario ahora ({topic.publish_report?.[0]?.problem}). No es un rechazo. Espera unos minutos y vuelve a pedir la publicación.
            </p>
          )}
          {topic.publish_status === "rejected" && topic.publish_report.length > 0 && (
            <div className="space-y-1 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              <p className="font-medium">No se ha publicado. La IA ha encontrado estos problemas.</p>
              <ul className="list-disc space-y-1 pl-5">
                {topic.publish_report.map((item, i) => (
                  <li key={i}>
                    {item.position ? <strong>Pregunta {item.position}. </strong> : null}
                    {item.question && <span className="text-red-500">{item.question} </span>}
                    {item.problem}
                  </li>
                ))}
              </ul>
              <p>Corrige el archivo, súbelo de nuevo con “Reemplazar preguntas” y pide la publicación otra vez.</p>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <Link to={`/practice/${topic.id}`} className="btn">Practicar</Link>
            {topic.visibility === "public" ? (
              <button className="btn-secondary" onClick={() => run(api.delete(`/topics/${topic.id}/publish/`))}>Volver a privado</button>
            ) : (
              topic.publish_status !== "pending" && (
                <button className="btn-secondary" onClick={() => run(api.post(`/topics/${topic.id}/publish/`))}>Publicar (verifica la IA)</button>
              )
            )}
            <button className="btn-secondary" onClick={() => { setReplacing(topic.id); input.current.click(); }}>Reemplazar preguntas</button>
            <button
              className="btn-secondary"
              onClick={() => window.confirm("¿Borrar este cuestionario y sus preguntas?") && run(api.delete(`/topics/${topic.id}/`))}
            >
              Borrar
            </button>
          </div>
        </div>
      ))}
    </section>
  );
}

export default function CreateTopic() {
  const [form, setForm] = useState({ name: "", description: "", visibility: "private", language: "es" }); // el idioma siempre es español
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [created, setCreated] = useState("");
  const [busy, setBusy] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setError("");
    setCreated("");
    setBusy(true);
    const body = new FormData();
    Object.entries(form).forEach(([key, value]) => body.append(key, value));
    body.append("file", file);
    try {
      const { data } = await api.post("/topics/", body);
      setCreated(data.name);
      setForm({ ...form, name: "", description: "" });
      setFile(null);
      event.target.reset();
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(fileErrors(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="page-title">Crear mi cuestionario</h1>
        <p className="max-w-3xl text-sm text-slate-500">
          Convierte tus propios apuntes en un cuestionario. Prepara un archivo JSON con al menos 20 preguntas de cuatro opciones, súbelo y practica cuando quieras.
          Si lo dejas privado, solo lo verás tú y tu chatbot. Si lo haces público, la IA lo revisa y, si todo es correcto, otros usuarios podrán practicarlo.
          Mira el formato a la derecha y descarga el archivo de ejemplo para empezar.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
      <form onSubmit={submit} className="card space-y-4">
        <input className="input" placeholder="Nombre del cuestionario, por ejemplo Java/SpringBoot" value={form.name} maxLength={80} onChange={update("name")} required />
        <input className="input" placeholder="Descripción (opcional)" value={form.description} maxLength={500} onChange={update("description")} />
        <div>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-500">Visibilidad</span>
            <select className="input" value={form.visibility} onChange={update("visibility")}>
              <option value="private">Privado. Solo para mí y mi chatbot, sin verificar</option>
              <option value="public">Público. Lo verifica la IA</option>
            </select>
          </label>
        </div>
        {form.visibility === "public" && (
          <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
            Un cuestionario público solo se publica si la IA da por buenas el 100% de las preguntas y respuestas. Si no, verás dónde está cada error.
          </p>
        )}
        <label className="block text-sm">
          <span className="mb-1 block text-slate-500">Archivo JSON con tus preguntas</span>
          <input type="file" accept=".json,application/json" onChange={(e) => setFile(e.target.files[0] || null)} className="block text-sm" required />
        </label>
        <ErrorList error={error} />
        {created && (
          <p className="text-sm text-green-700">
            Cuestionario creado. {created}
            {form.visibility === "private" && " Es privado, así que no se ha verificado con IA. Cuando lo hagas público, la IA revisará las respuestas."}
          </p>
        )}
        <button className="btn" disabled={busy || !file}>{busy ? "Creando" : "Crear cuestionario"}</button>
      </form>
      <FormatExample />
      </div>

      <MyCreated reloadKey={reloadKey} />
    </div>
  );
}
