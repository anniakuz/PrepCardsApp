import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { LEVEL_LABELS, errorText } from "../api.js";
import LevelBadge from "../components/LevelBadge.jsx";
import QuestionTools from "../components/QuestionTools.jsx";

export default function Practice() {
  const { topicId } = useParams();
  const [topic, setTopic] = useState(null);
  const [round, setRound] = useState(null);
  const [resumable, setResumable] = useState(null);
  const [level, setLevel] = useState(2);
  const [fixed, setFixed] = useState(false);
  const [selected, setSelected] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setRound(null);
    setFeedback(null);
    Promise.all([
      api.get(`/topics/${topicId}/`),
      api.get(`/topics/${topicId}/level/`),
      api.get(`/topics/${topicId}/active-round/`).catch(() => ({ data: null })),
    ])
      .then(([t, l, r]) => {
        setTopic(t.data);
        setLevel(l.data.level);
        setFixed(l.data.fixed);
        setResumable(r.data);
      })
      .catch((err) => setError(errorText(err)));
  }, [topicId]);

  async function start(resume = false) {
    setError("");
    try {
      if (resume) {
        setRound(resumable);
      } else {
        const body = { topic: Number(topicId) };
        if (topic.uses_levels && !fixed) body.level = level;
        const { data } = await api.post("/rounds/", body);
        setRound(data);
        setFixed(true);
      }
      setSelected(null);
      setFeedback(null);
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function answer(choiceId) {
    if (busy || feedback) return;
    setSelected(choiceId);
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post(`/rounds/${round.id}/answer/`, { choice: choiceId });
      setFeedback({ ...data, chosen: choiceId });
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  function next() {
    setRound(feedback.round);
    setFeedback(null);
    setSelected(null);
  }

  if (error && !topic) return <p className="text-red-600">{error}</p>;
  if (!topic) return <p className="text-slate-500">Cargando</p>;

  const header = (
    <div>
      <Link to="/my-topics" className="text-sm text-indigo-600">Volver a mis temas</Link>
      <h1 className="page-title">{topic.name}</h1>
      {topic.owner_name && <p className="text-sm text-slate-500">Creado por {topic.owner_name}</p>}
      {topic.description && <p className="max-w-3xl text-sm text-slate-500">{topic.description}</p>}
    </div>
  );

  if (!round) {
    return (
      <div className="space-y-6">
        {header}
        <div className="card max-w-xl space-y-4">
          <p className="text-sm text-slate-600">
            Una ronda tiene al menos 20 preguntas.
            {topic.uses_levels && " Con cinco aciertos seguidos subes de nivel y con tres fallos seguidos bajas."}
          </p>
          {topic.uses_levels && fixed && (
            <div className="rounded-xl bg-indigo-50 p-4 text-sm text-slate-700">
              <p className="mb-1 font-medium">Tu nivel actual</p>
              <LevelBadge level={level} />
              <p className="mt-2 text-slate-500">
                El nivel de partida ya está fijado. A partir de ahora solo cambia al responder: cinco aciertos seguidos suben un nivel y tres fallos seguidos lo bajan.
              </p>
            </div>
          )}
          {topic.uses_levels && !fixed && (
            <div>
              <p className="mb-1 text-sm font-medium">Nivel con el que empiezas</p>
              <p className="mb-2 text-xs text-slate-500">Elígelo con cuidado. Cuando empieces el tema quedará fijado y solo podrá subir o bajar según tus respuestas.</p>
              <div className="flex flex-wrap gap-2">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    onClick={() => setLevel(n)}
                    className={`rounded-lg border px-3 py-2 text-sm ${
                      level === n ? "border-indigo-600 bg-indigo-600 text-white" : "border-slate-300 bg-white hover:border-indigo-400"
                    }`}
                  >
                    {n} · {LEVEL_LABELS[n]}
                  </button>
                ))}
              </div>
            </div>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex flex-wrap gap-2">
            <button className="btn" onClick={() => start(false)}>Empezar ronda nueva</button>
            {resumable && (
              <button className="btn-secondary" onClick={() => start(true)}>
                Continuar ronda ({resumable.answered}/{resumable.size})
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (round.status !== "active" && !feedback) {
    return (
      <div className="space-y-6">
        {header}
        <div className="card max-w-xl space-y-3 text-center">
          <h2 className="text-xl font-semibold">Ronda terminada</h2>
          <p className="text-3xl font-bold">{round.correct} / {round.answered}</p>
          {round.uses_levels && <p><LevelBadge level={round.level} prefix="Tu nivel ahora" /></p>}
          <div className="flex justify-center gap-2">
            <button className="btn" onClick={() => { setRound(null); setResumable(null); api.get(`/topics/${topicId}/level/`).then(({ data }) => setLevel(data.level)); }}>
              Otra ronda
            </button>
            <Link className="btn-secondary" to="/stats">Ver estadísticas</Link>
          </div>
        </div>
      </div>
    );
  }

  const question = round.question;
  const current = feedback ? feedback.round : round;
  const finished = feedback && feedback.round.status !== "active";
  const progress = Math.round(((feedback ? feedback.round.answered : round.answered) / round.size) * 100);

  return (
    <div className="space-y-6">
      {header}
      <div className="h-3 overflow-hidden rounded-full bg-slate-200/80">
        <div className="h-full bg-gradient-to-r from-indigo-500 to-fuchsia-500 transition-all duration-500" style={{ width: `${progress}%` }} />
      </div>
      <div className="card max-w-3xl space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-500">
          <span>Pregunta {round.answered + 1} de {round.size}</span>
          <div className="flex gap-2">
            <LevelBadge level={question.level} prefix="Esta pregunta. Nivel" />
            {round.uses_levels && <LevelBadge level={current.level} prefix="Tu nivel" />}
          </div>
        </div>
        <p className="text-lg font-medium">{question.text}</p>
        <div className="space-y-2">
          {question.choices.map((choice) => {
            let style = "border-slate-300 bg-white hover:border-indigo-400";
            if (feedback) {
              if (choice.id === feedback.correct_choice) style = "border-green-500 bg-green-50 animate-pop";
              else if (choice.id === feedback.chosen) style = "border-red-400 bg-red-50 animate-shake";
              else style = "border-slate-200 bg-white opacity-60";
            } else if (selected === choice.id) style = "border-indigo-600 bg-indigo-50 ring-2 ring-indigo-200";
            return (
              <button
                key={choice.id}
                disabled={Boolean(feedback) || busy}
                onClick={() => answer(choice.id)}
                className={`block w-full rounded-xl border px-4 py-3 text-left text-sm transition duration-150 hover:-translate-y-px hover:shadow-sm ${style}`}
              >
                {choice.text}
              </button>
            );
          })}
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!feedback ? (
          <p className="text-sm text-slate-400">Pulsa una opción para responder.</p>
        ) : (
          <div className="space-y-3">
            <p className={`font-semibold ${feedback.correct ? "text-green-700" : "text-red-600"}`}>
              {feedback.correct ? "✓ Correcto" : "✗ Incorrecto"}
            </p>
            {feedback.level_change === "up" && <p className="animate-pop rounded-xl bg-emerald-50 p-3 text-sm font-medium text-emerald-700">🎉 Subes al nivel {feedback.round.level}. Cinco aciertos seguidos.</p>}
            {feedback.level_change === "down" && <p className="animate-fade-up rounded-xl bg-amber-50 p-3 text-sm text-amber-700">Bajas al nivel {feedback.round.level}. Tres fallos seguidos.</p>}
            {feedback.explanation && <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{feedback.explanation}</p>}
            <button className="btn" onClick={next}>{finished ? "Ver resultado" : "Siguiente pregunta"}</button>
          </div>
        )}
        <QuestionTools question={question} />
      </div>
    </div>
  );
}
