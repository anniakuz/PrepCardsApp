import { Link } from "react-router-dom";
import LevelBadge from "./LevelBadge.jsx";

const ACCENTS = ["from-indigo-500 to-violet-500", "from-sky-500 to-indigo-500", "from-emerald-500 to-teal-500", "from-amber-500 to-orange-500", "from-rose-500 to-pink-500", "from-fuchsia-500 to-purple-500"];

export default function TopicCard({ topic, onJoin, onLeave, highlight = false, children }) {
  return (
    <div className={`card card-hover relative flex flex-col justify-between gap-4 overflow-hidden ${highlight ? "border-indigo-300 bg-indigo-50/40" : ""}`}>
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${ACCENTS[topic.id % ACCENTS.length]}`} />
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="break-words font-semibold">{topic.name}</h3>
          {topic.visibility === "official" && <span className="badge bg-indigo-100 text-indigo-700">Oficial</span>}
          {topic.visibility === "private" && <span className="badge">Privado</span>}
        </div>
        {topic.owner_name && <p className="text-xs text-slate-500">Creado por {topic.owner_name}</p>}
        {topic.description && <p className="text-sm text-slate-500">{topic.description}</p>}
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span>{topic.question_count} preguntas</span>
          <span>{topic.learners} {topic.learners === 1 ? "alumno" : "alumnos"}</span>
          {topic.level && <LevelBadge level={topic.level} />}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Link to={`/practice/${topic.id}`} className="btn">Practicar</Link>
        {onJoin && !topic.is_mine_to_practice && <button className="btn-secondary" onClick={() => onJoin(topic)}>Añadir a mis temas</button>}
        {onLeave && <button className="btn-secondary" onClick={() => onLeave(topic)}>Quitar</button>}
      </div>
      {children}
    </div>
  );
}
