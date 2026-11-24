import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import api, { errorText } from "../api.js";
import QuestionTools from "../components/QuestionTools.jsx";
import { VERDICTS } from "./OfferDetail.jsx";

function AddToLibrary({ topic }) {
  const [state, setState] = useState("idle");
  async function add() {
    setState("busy");
    try {
      await api.post(`/topics/${topic.id}/join/`);
      setState("done");
    } catch {
      setState("idle");
    }
  }
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm">
      <span>
        <Link to={`/practice/${topic.id}`} className="font-medium hover:text-indigo-600">{topic.name}</Link>
        {topic.reinforce && <span className="badge ml-2 !bg-amber-100 !text-amber-800">Conviene reforzar</span>}
        <span className="ml-2 text-xs text-slate-400">Por {topic.requirements.join(", ")}</span>
      </span>
      {state === "done" ? (
        <span className="text-green-700">Añadido a Mi biblioteca</span>
      ) : (
        <button className="btn-secondary !py-1" disabled={state === "busy"} onClick={add}>Añadir a Mi biblioteca</button>
      )}
    </div>
  );
}

function Result({ offerId, result }) {
  const [label, style] = VERDICTS[result.verdict];
  return (
    <div className="card max-w-3xl space-y-5">
      <div className={`rounded-xl p-4 ${style}`}>
        <p className="text-lg font-semibold">{label}</p>
        {result.missing_required.length > 0 && (
          <p className="mt-1 text-sm">Requisitos obligatorios sin cumplir: {result.missing_required.join(", ")}.</p>
        )}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-500">Aciertos</p>
          <p className="text-4xl font-bold">{result.accuracy}%</p>
          <p className="text-sm text-slate-400">{result.correct} de {result.total} preguntas</p>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-500">Compatibilidad con la oferta</p>
          <p className="text-4xl font-bold">{result.compatibility}%</p>
          <p className="text-sm text-slate-400">Cuentan todos los requisitos de la oferta</p>
        </div>
      </div>
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Por requisito</p>
        {result.requirements.map((r) => (
          <div key={r.name} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm">
            <span className="font-medium">
              {r.name} <span className="font-normal text-slate-400">({r.importance === "required" ? "obligatorio" : "valorable"})</span>
            </span>
            <span className="flex items-center gap-2">
              {r.evaluated ? <span className="text-slate-500">{r.correct} de {r.answered}</span> : <span className="text-slate-400">No evaluado</span>}
              <span className={`badge ${r.met ? "!bg-green-100 !text-green-700" : "!bg-red-100 !text-red-700"}`}>
                {r.met ? "Cumple" : "No cumple"}
              </span>
            </span>
          </div>
        ))}
      </div>
      {result.recommended_topics?.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Temas oficiales recomendados</p>
          <p className="text-sm text-slate-500">
            Son temas oficiales relacionados con la oferta. Añade a tu biblioteca los que quieras practicar. Los marcados conviene reforzarlos porque no has cumplido ese requisito.
          </p>
          <div className="space-y-2">
            {result.recommended_topics.map((t) => <AddToLibrary key={t.id} topic={t} />)}
          </div>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <Link to={`/offers/${offerId}`} className="btn-secondary">Volver a la oferta</Link>
        <Link to="/my-topics" className="btn-secondary">Ir a Mi biblioteca</Link>
      </div>
    </div>
  );
}

function Review({ review }) {
  const [open, setOpen] = useState(null);
  return (
    <section className="max-w-3xl space-y-3">
      <div>
        <h2 className="text-lg font-semibold">Preguntas que has respondido</h2>
        <p className="text-sm text-slate-500">Repásalas con su explicación. Si algo no te queda claro, pregunta al chatbot o envíala a tu mentor.</p>
      </div>
      {review.map((q, index) => (
        <div key={q.id} className="card space-y-3">
          <button className="w-full text-left" onClick={() => setOpen(open === q.id ? null : q.id)}>
            <div className="mb-1 flex flex-wrap gap-2">
              <span className="badge">{index + 1}</span>
              <span className="badge">{q.requirement}</span>
              <span className={`badge ${q.correct ? "!bg-green-100 !text-green-700" : "!bg-red-100 !text-red-700"}`}>
                {q.correct ? "Acertada" : "Fallada"}
              </span>
            </div>
            <p className="font-medium">{q.text}</p>
          </button>
          {open === q.id && (
            <>
              <ul className="space-y-1 text-sm">
                {q.choices.map((c) => (
                  <li key={c.id} className={c.is_correct ? "font-semibold text-green-700" : c.id === q.chosen ? "font-semibold text-red-600" : "text-slate-600"}>
                    {c.is_correct ? "✓ " : c.id === q.chosen ? "✗ " : "· "}{c.text}
                    {c.id === q.chosen && " (tu respuesta)"}
                  </li>
                ))}
              </ul>
              {q.explanation && <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{q.explanation}</p>}
              <QuestionTools question={q} canSave={false} />
            </>
          )}
        </div>
      ))}
    </section>
  );
}

export default function OfferQuiz() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const [attempt, setAttempt] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const seen = params.get("attempt");
    const request = seen ? api.get(`/offers/${id}/attempts/${seen}/`) : api.post(`/offers/${id}/attempts/`);
    request.then(({ data }) => setAttempt(data)).catch((err) => setError(errorText(err)));
  }, [id]);

  async function answer(choiceId) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post(`/offers/${id}/attempts/${attempt.id}/answer/`, { choice: choiceId });
      setAttempt(data);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  if (error && !attempt) return <p className="text-red-600">{error}</p>;
  if (!attempt) return <p className="text-slate-500">Cargando</p>;

  const header = (
    <div>
      <Link to={`/offers/${id}`} className="text-sm text-indigo-600">Volver a la oferta</Link>
      <h1 className="page-title">Cuestionario de la oferta</h1>
    </div>
  );

  if (attempt.status === "finished") {
    return (
      <div className="space-y-6">
        {header}
        <Result offerId={id} result={attempt.result} />
        {attempt.review?.length > 0 && <Review review={attempt.review} />}
      </div>
    );
  }

  const progress = Math.round((attempt.answered / attempt.total) * 100);
  return (
    <div className="space-y-6">
      {header}
      <div className="h-3 overflow-hidden rounded-full bg-slate-200/80">
        <div className="h-full bg-gradient-to-r from-indigo-500 to-fuchsia-500 transition-all duration-500" style={{ width: `${progress}%` }} />
      </div>
      <div className="card max-w-3xl space-y-5">
        <p className="text-sm text-slate-500">Pregunta {attempt.answered + 1} de {attempt.total}</p>
        <p className="text-lg font-medium">{attempt.question.text}</p>
        <div className="space-y-2">
          {attempt.question.choices.map((choice) => (
            <button
              key={choice.id}
              disabled={busy}
              onClick={() => answer(choice.id)}
              className="block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-left text-sm transition duration-150 hover:-translate-y-px hover:border-indigo-400 hover:shadow-sm disabled:opacity-60"
            >
              {choice.text}
            </button>
          ))}
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <p className="text-sm text-slate-400">Pulsa una opción para responder. No se muestra si has acertado hasta el final.</p>
      </div>
    </div>
  );
}
