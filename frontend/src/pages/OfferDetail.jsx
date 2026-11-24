import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api, { errorText } from "../api.js";
import LevelBadge from "../components/LevelBadge.jsx";

const CATEGORY_LABELS = {
  language: "Lenguajes",
  framework: "Frameworks",
  database: "Bases de datos",
  cloud: "Cloud",
  devops: "DevOps",
  architecture: "Arquitectura",
  testing: "Testing",
  soft_skill: "Habilidades blandas",
  other: "Otros",
};

export const VERDICTS = {
  compatible: ["Compatible con la oferta", "text-green-700 bg-green-50"],
  partial: ["Compatible en parte", "text-amber-700 bg-amber-50"],
  not_compatible: ["Todavía no eres compatible", "text-red-700 bg-red-50"],
};

const inProgress = (offer) => offer.status === "pending" || offer.generation_status === "running";

export default function OfferDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [offer, setOffer] = useState(null);
  const [selected, setSelected] = useState(null);
  const [count, setCount] = useState(20);
  const [error, setError] = useState("");
  const timer = useRef(null);

  // El análisis y la generación corren en Celery. Se consulta la oferta hasta que terminan.
  function load() {
    api
      .get(`/offers/${id}/`)
      .then(({ data }) => {
        setOffer(data);
        setSelected((current) =>
          current ?? (data.status === "ready"
            ? (data.selected_requirements.length ? data.selected_requirements : data.requirements.map((r) => r.name))
            : null)
        );
        if (inProgress(data)) timer.current = setTimeout(load, 2000);
      })
      .catch((err) => setError(errorText(err)));
  }

  useEffect(() => {
    load();
    return () => clearTimeout(timer.current);
  }, [id]);

  if (error && !offer) return <p className="text-red-600">{error}</p>;
  if (!offer) return <p className="text-slate-500">Cargando</p>;

  async function remove() {
    if (!window.confirm("¿Borrar esta oferta y su cuestionario?")) return;
    await api.delete(`/offers/${id}/`);
    navigate("/offers");
  }

  async function reviewText() {
    await api.delete(`/offers/${id}/`);
    navigate("/offers", { state: { text: offer.raw_text } });
  }

  const header = (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <Link to="/offers" className="text-sm text-indigo-600">Volver a ofertas</Link>
        <h1 className="page-title">{offer.title || "Oferta sin título"}</h1>
        <p className="text-sm text-slate-500">{offer.company}</p>
      </div>
      <button className="btn-secondary" onClick={remove}>Borrar</button>
    </div>
  );

  if (offer.status === "pending") {
    return (
      <div className="space-y-6">
        {header}
        <div className="card space-y-2 text-slate-600">
          <p>Analizando la oferta. Suele tardar unos segundos.</p>
          {offer.error && <p className="text-sm text-amber-700">{offer.error}. Puede tardar un par de minutos, no cierres la página.</p>}
        </div>
      </div>
    );
  }
  if (offer.status === "invalid") {
    return (
      <div className="space-y-6">
        {header}
        <div className="card space-y-3 border-amber-300">
          <h2 className="text-lg font-semibold text-amber-700">No se puede generar el cuestionario</h2>
          <p className="text-sm text-slate-600">
            El texto no tiene requisitos técnicos concretos. Revísalo y vuelve a intentarlo. Por ejemplo, programador no es un requisito, pero programador Java sí.
          </p>
          {offer.error && <p className="text-sm text-slate-500">{offer.error}</p>}
          <button className="btn" onClick={reviewText}>Revisar el texto</button>
        </div>
      </div>
    );
  }
  if (offer.status === "failed") {
    return (
      <div className="space-y-6">
        {header}
        <p className="card text-red-600">No se pudo analizar la oferta. {offer.error}</p>
      </div>
    );
  }

  const chosen = selected ?? [];
  const groups = {};
  offer.requirements.forEach((req) => {
    (groups[req.category] ||= []).push(req);
  });
  const generating = offer.generation_status === "running";
  const canForty = chosen.length > 3;
  const amount = canForty ? count : 20;
  const hasQuiz = offer.question_count > 0;

  function setAmount(value) {
    setCount(value);
  }

  function toggle(name) {
    setSelected(chosen.includes(name) ? chosen.filter((n) => n !== name) : [...chosen, name]);
  }

  async function generate() {
    if (hasQuiz && !window.confirm("Se creará un cuestionario nuevo y se borrarán los resultados anteriores. ¿Continuar?")) return;
    setError("");
    try {
      const { data } = await api.post(`/offers/${id}/generate/`, { requirements: chosen, count: amount });
      setOffer(data);
      clearTimeout(timer.current);
      timer.current = setTimeout(load, 2000);
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <div className="space-y-6">
      {header}
      {offer.summary && <p className="card text-sm text-slate-600">{offer.summary}</p>}

      <div className="card flex flex-wrap items-center gap-3">
        {offer.level > 0 ? (
          <>
            <span className="text-sm text-slate-500">Nivel que pide la oferta</span>
            <LevelBadge level={offer.level} />
            {offer.level_reason && <span className="text-sm text-slate-500">({offer.level_reason})</span>}
          </>
        ) : (
          <span className="text-sm text-slate-500">La oferta no indica el nivel. Se usan preguntas de nivel intermedio.</span>
        )}
      </div>

      {offer.suggested_topics.length > 0 && (
        <div className="card space-y-3">
          <div>
            <h2 className="text-lg font-semibold">Temas oficiales recomendados</h2>
            <p className="text-sm text-slate-500">Para prepararte antes del cuestionario. Se practican por separado, con niveles.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {offer.suggested_topics.map((t) => (
              <Link key={t.id} to={`/practice/${t.id}`} className="badge hover:bg-indigo-100">{t.name}</Link>
            ))}
          </div>
        </div>
      )}

      <div className="card space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Requisitos detectados</h2>
          <p className="text-sm text-slate-500">
            Elige los que quieres que evalúe el cuestionario. Los que dejes fuera cuentan como no demostrados al calcular tu compatibilidad.
          </p>
        </div>
        {Object.entries(groups).map(([category, reqs]) => (
          <div key={category}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              {CATEGORY_LABELS[category] || category}
            </p>
            <div className="flex flex-wrap gap-2">
              {reqs.map((req) => {
                const active = chosen.includes(req.name);
                return (
                  <button
                    key={req.name}
                    onClick={() => toggle(req.name)}
                    className={`rounded-full border px-3 py-1 text-sm transition ${
                      active
                        ? "border-indigo-600 bg-indigo-600 text-white"
                        : "border-slate-300 bg-white text-slate-600 hover:border-indigo-400"
                    }`}
                  >
                    {req.name}
                    <span className="ml-1 opacity-70">({req.importance === "required" ? "obligatorio" : "valorable"})</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
        <div className="space-y-2 border-t border-slate-200 pt-4">
          <p className="text-sm font-medium">Número de preguntas</p>
          <div className="flex flex-wrap gap-2">
            {[20, 40].map((n) => (
              <button
                key={n}
                type="button"
                disabled={n === 40 && !canForty}
                onClick={() => setAmount(n)}
                className={`rounded-xl border px-4 py-1.5 text-sm transition disabled:cursor-not-allowed disabled:opacity-40 ${
                  amount === n ? "border-indigo-600 bg-indigo-600 text-white" : "border-slate-300 bg-white text-slate-600 hover:border-indigo-400"
                }`}
              >
                {n} preguntas
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            El cuestionario de 40 preguntas solo está disponible si eliges más de tres requisitos. Los obligatorios pesan el 90% de la compatibilidad y los valorables el 10%.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn" onClick={generate} disabled={generating || chosen.length === 0}>
            {generating ? "Creando el cuestionario" : hasQuiz ? "Crear cuestionario de nuevo" : "Crear cuestionario"}
          </button>
          {generating && <span className="text-sm text-slate-500">Puede tardar un poco si hay que generar preguntas.</span>}
        </div>
        {offer.generation_status === "failed" && (
          <p className="text-sm text-red-600">No se pudo crear el cuestionario. {offer.generation_error}</p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      {hasQuiz && (
        <div className="card space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">Cuestionario de la oferta</h2>
              <p className="text-sm text-slate-500">{offer.question_count} preguntas sobre {offer.selected_requirements.join(", ")}.</p>
            </div>
            <Link to={`/offers/${id}/quiz`} className="btn">{offer.attempts.length ? "Repetir cuestionario" : "Hacer cuestionario"}</Link>
          </div>
          {offer.attempts.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Tus intentos</p>
              {offer.attempts.map((a) => (
                <Link key={a.id} to={`/offers/${id}/quiz?attempt=${a.id}`} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm hover:border-indigo-300">
                  <span>{new Date(a.finished_at).toLocaleString()}</span>
                  <span className="flex gap-2">
                    <span className="badge">Aciertos {a.accuracy}%</span>
                    <span className="badge">Compatibilidad {a.compatibility}%</span>
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
