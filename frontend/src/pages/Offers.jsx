import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import api, { errorText } from "../api.js";

const STATUS = { pending: "Analizando", failed: "Error", invalid: "Texto no válido" };

export default function Offers() {
  const navigate = useNavigate();
  const location = useLocation();
  const [offers, setOffers] = useState([]);
  const [text, setText] = useState(location.state?.text || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/offers/")
      .then(({ data }) => setOffers(data))
      .catch((err) => setError(errorText(err)));
  }, []);

  async function analyze(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { data } = await api.post("/offers/", { raw_text: text });
      navigate(`/offers/${data.id}`);
    } catch (err) {
      setError(errorText(err));
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Análisis de oferta de trabajo</h1>
        <p className="text-sm text-slate-500">
          Pega el texto de una oferta. Se detectan sus requisitos y el nivel que pide, eliges cuáles evaluar y haces un cuestionario de 20 o 40 preguntas para saber si eres compatible. Los requisitos obligatorios pesan el 90% de la compatibilidad y los valorables el 10%. Al terminar te recomendamos temas oficiales para reforzar lo que te falte y tú decides cuáles añadir a Mi biblioteca.
        </p>
      </div>

      <form onSubmit={analyze} className="card space-y-3">
        <textarea
          className="input h-48 resize-y"
          placeholder="Pega aquí el texto completo de la oferta"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="btn" disabled={busy || !text.trim()}>
          {busy ? "Enviando" : "Analizar oferta"}
        </button>
      </form>

      {offers.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Ofertas analizadas</h2>
          {offers.map((offer) => (
            <Link key={offer.id} to={`/offers/${offer.id}`} className="card block hover:border-indigo-300">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-semibold">{offer.title || "Oferta sin título"}</p>
                  <p className="text-sm text-slate-500">{offer.company}</p>
                </div>
                <div className="flex gap-2">
                  {STATUS[offer.status] && <span className="badge">{STATUS[offer.status]}</span>}
                  <span className="badge">{offer.requirements.length} requisitos</span>
                  <span className="badge">{offer.question_count} preguntas</span>
                  {offer.attempts?.[0] && <span className="badge">Compatibilidad {offer.attempts[0].compatibility}%</span>}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
