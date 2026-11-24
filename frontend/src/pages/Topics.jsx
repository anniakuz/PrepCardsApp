import { useEffect, useState } from "react";
import api, { errorText } from "../api.js";
import TopicCard from "../components/TopicCard.jsx";

function Catalog({ kind, title, intro, empty, search, onJoin, joined }) {
  const [topics, setTopics] = useState([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => setPage(1), [search]);

  useEffect(() => {
    api
      .get("/topics/", { params: { q: search, page, kind, ordering: "popular" } })
      .then(({ data }) => {
        setTopics(data.results);
        setCount(data.count);
      })
      .catch((err) => setError(errorText(err)));
  }, [search, page, kind]);

  const pages = Math.max(1, Math.ceil(count / 12));
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-sm text-slate-500">{intro}</p>
      </div>
      {error && <p className="text-red-600">{error}</p>}
      {topics.length === 0 && <p className="card text-sm text-slate-500">{empty}</p>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {topics.map((topic) => (
          <TopicCard key={topic.id} topic={joined.has(topic.id) ? { ...topic, is_mine_to_practice: true } : topic} onJoin={onJoin} />
        ))}
      </div>
      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 text-sm">
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
          <span>Página {page} de {pages}</span>
          <button className="btn-secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>Siguiente</button>
        </div>
      )}
    </section>
  );
}

export default function Topics() {
  const [popular, setPopular] = useState([]);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [joined, setJoined] = useState(new Set());

  useEffect(() => {
    api.get("/topics/popular/").then(({ data }) => setPopular(data)).catch(() => {});
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => setSearch(query.trim()), 250);
    return () => clearTimeout(timer);
  }, [query]);

  async function join(topic) {
    await api.post(`/topics/${topic.id}/join/`);
    setJoined((current) => new Set(current).add(topic.id));
  }

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="page-title">Temas</h1>
        <p className="max-w-3xl text-sm text-slate-500">
          Aquí encuentras todo lo que puedes practicar. Los temas oficiales los prepara PrepCards y cubren las aptitudes más pedidas en las entrevistas.
          Cada tema empieza en el nivel que elijas y después sube o baja según tus respuestas, así siempre practicas a tu medida.
          Añade un tema a Mi biblioteca para tenerlo a mano y ver tu progreso en Estadísticas.
        </p>
      </div>

      {!search && popular.length > 0 && (
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-semibold">Los más populares</h2>
            <p className="text-sm text-slate-500">Los temas que más practican el resto de alumnos esta semana.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {popular.map((topic) => (
              <TopicCard key={topic.id} topic={joined.has(topic.id) ? { ...topic, is_mine_to_practice: true } : topic} onJoin={join} highlight />
            ))}
          </div>
        </section>
      )}

      <input
        className="input max-w-md"
        placeholder="Buscar por nombre o creador"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      <Catalog
        kind="official"
        title="Temas oficiales"
        intro="Preguntas revisadas por PrepCards, ordenadas por nivel del 1 al 5, con explicación en cada respuesta."
        empty="No hay temas oficiales que coincidan con tu búsqueda."
        search={search}
        onJoin={join}
        joined={joined}
      />
      <Catalog
        kind="community"
        title="Todos los demás: cuestionarios de otros usuarios"
        intro="Solo incluye cuestionarios creados por otros usuarios o públicos y verificados con IA. Un cuestionario público solo aparece aquí cuando la IA lo ha revisado por completo."
        empty="Todavía no hay cuestionarios de otros usuarios que coincidan."
        search={search}
        onJoin={join}
        joined={joined}
      />
    </div>
  );
}
