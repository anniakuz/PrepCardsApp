import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorText } from "../api.js";
import LevelBadge from "../components/LevelBadge.jsx";
import QuestionTools from "../components/QuestionTools.jsx";
import TopicCard from "../components/TopicCard.jsx";

function SavedQuestions() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ count: 0, results: [] });
  const [open, setOpen] = useState(null);

  useEffect(() => {
    api.get("/saved/", { params: { page } }).then(({ data }) => setData(data));
  }, [page]);

  const pages = Math.max(1, Math.ceil(data.count / 12));
  if (data.count === 0) return <p className="card text-sm text-slate-500">Aún no has guardado preguntas. Guárdalas durante la práctica para verlas aquí.</p>;
  return (
    <div className="space-y-3">
      {data.results.map((question) => (
        <div key={question.id} className="card space-y-3">
          <button className="w-full text-left" onClick={() => setOpen(open === question.id ? null : question.id)}>
            <div className="mb-1 flex flex-wrap gap-2">
              <span className="badge">{question.topic_name}</span>
              <LevelBadge level={question.level} />
            </div>
            <p className="font-medium">{question.text}</p>
          </button>
          {open === question.id && (
            <>
              <ul className="space-y-1 text-sm">
                {question.choices.map((choice) => (
                  <li key={choice.id} className={choice.is_correct ? "font-semibold text-green-700" : "text-slate-600"}>
                    {choice.is_correct ? "✓ " : "· "}{choice.text}
                  </li>
                ))}
              </ul>
              {question.explanation && <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{question.explanation}</p>}
              <QuestionTools question={{ ...question, saved: true }} />
            </>
          )}
        </div>
      ))}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 text-sm">
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
          <span>Página {page} de {pages}</span>
          <button className="btn-secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>Siguiente</button>
        </div>
      )}
    </div>
  );
}

const PUBLISH = { pending: "Verificando con IA", approved: "Publicado", rejected: "Rechazado por la IA", error: "No se pudo verificar" };

function Visibility({ topic, onChange }) {
  const [error, setError] = useState("");
  const isPublic = topic.visibility === "public";
  const pending = topic.publish_status === "pending";

  async function run(promise) {
    setError("");
    try {
      await promise;
      onChange();
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <div className="space-y-2 border-t border-slate-200 pt-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="badge">{isPublic ? "Público" : "Privado"}</span>
        {topic.publish_status && <span className="badge">{PUBLISH[topic.publish_status]}</span>}
      </div>
      {topic.publish_status === "error" && (
        <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
          La IA no ha podido verificarlo ahora ({topic.publish_report?.[0]?.problem}). No es un rechazo, inténtalo de nuevo en unos minutos.
        </p>
      )}
      {topic.publish_status === "rejected" && topic.publish_report?.length > 0 && (
        <ul className="list-disc space-y-1 rounded-lg bg-red-50 p-3 pl-6 text-xs text-red-700">
          {topic.publish_report.slice(0, 5).map((item, i) => (
            <li key={i}>{item.position ? `Pregunta ${item.position}. ` : ""}{item.problem}</li>
          ))}
        </ul>
      )}
      {isPublic ? (
        <button className="btn-secondary w-full" onClick={() => run(api.delete(`/topics/${topic.id}/publish/`))}>Volver a privado</button>
      ) : (
        <button className="btn-secondary w-full" disabled={pending} onClick={() => run(api.post(`/topics/${topic.id}/publish/`))}>
          {pending ? "La IA lo está verificando" : "Hacer público (lo verifica la IA antes)"}
        </button>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

export default function MyTopics() {
  const [tab, setTab] = useState("topics");
  const [topics, setTopics] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get("/topics/mine/").then(({ data }) => setTopics(data)).catch((err) => setError(errorText(err)));
  }, []);
  useEffect(load, [load]);
  // La verificación con IA tarda unos segundos. Se consulta mientras haya cuestionarios verificándose
  useEffect(() => {
    if (!topics?.some((t) => t.publish_status === "pending")) return;
    const timer = setTimeout(load, 2500);
    return () => clearTimeout(timer);
  }, [topics, load]);

  async function leave(topic) {
    await api.delete(`/topics/${topic.id}/join/`);
    setTopics((current) => current.filter((t) => t.id !== topic.id));
  }

  const official = (topics || []).filter((t) => t.visibility === "official");
  const quizzes = (topics || []).filter((t) => t.visibility !== "official");
  const tabClass = (name) =>
    `rounded-lg px-4 py-2 text-sm font-medium ${tab === name ? "bg-indigo-600 text-white" : "bg-white text-slate-600 hover:bg-slate-100"}`;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Mi biblioteca</h1>
        <p className="max-w-3xl text-sm text-slate-500">
          Tu punto de partida. Aquí tienes los temas oficiales que practicas, los cuestionarios que has creado o guardado y las preguntas
          que marcaste durante la práctica. Los temas que te recomienda un cuestionario de oferta se añaden solos en Temas oficiales.
        </p>
      </div>
      <div className="flex gap-2">
        <button className={tabClass("topics")} onClick={() => setTab("topics")}>Temas y cuestionarios</button>
        <button className={tabClass("saved")} onClick={() => setTab("saved")}>Preguntas guardadas</button>
      </div>
      {error && <p className="text-red-600">{error}</p>}
      {tab === "saved" ? (
        <SavedQuestions />
      ) : topics === null ? (
        <p className="text-slate-500">Cargando</p>
      ) : topics.length === 0 ? (
        <div className="card text-sm text-slate-600">
          Todavía no tienes nada aquí. Mira el <Link className="font-medium text-indigo-600" to="/topics">catálogo de temas</Link> o{" "}
          <Link className="font-medium text-indigo-600" to="/create">crea tu primer cuestionario</Link>.
        </div>
      ) : (
        <>
          <section className="space-y-3">
            <div>
              <h2 className="text-lg font-semibold">Temas oficiales</h2>
              <p className="text-sm text-slate-500">Preparados por PrepCards. Tu nivel en cada uno sube o baja según respondes.</p>
            </div>
            {official.length === 0 ? (
              <p className="card text-sm text-slate-500">Aún no has añadido temas oficiales.</p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {official.map((topic) => (
                  <TopicCard key={topic.id} topic={{ ...topic, is_mine_to_practice: true }} onLeave={leave} />
                ))}
              </div>
            )}
          </section>
          <section className="space-y-3">
            <div>
              <h2 className="text-lg font-semibold">Mis cuestionarios</h2>
              <p className="text-sm text-slate-500">Los que has creado tú y los de otros usuarios que has guardado. En los tuyos puedes cambiar entre público y privado. Para hacerlo público, la IA revisa antes todas las preguntas y respuestas.</p>
            </div>
            {quizzes.length === 0 ? (
              <p className="card text-sm text-slate-500">
                Todavía no tienes cuestionarios. <Link className="font-medium text-indigo-600" to="/create">Crea uno</Link> subiendo tus preguntas.
              </p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {quizzes.map((topic) => (
                  <TopicCard key={topic.id} topic={{ ...topic, is_mine_to_practice: true }} onLeave={topic.mine ? null : leave}>
                    {topic.mine && <Visibility topic={topic} onChange={load} />}
                  </TopicCard>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
