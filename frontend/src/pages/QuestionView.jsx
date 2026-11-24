import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorText } from "../api.js";
import LevelBadge from "../components/LevelBadge.jsx";
import QuestionTools from "../components/QuestionTools.jsx";

/** Pregunta abierta desde el chat con un mentor. La respuesta se ve solo si ya se ha respondido o guardado. */
export default function QuestionView() {
  const { id } = useParams();
  const [question, setQuestion] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/questions/${id}/`).then(({ data }) => setQuestion(data)).catch((err) => setError(errorText(err)));
  }, [id]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!question) return <p className="text-slate-500">Cargando</p>;
  const revealed = "explanation" in question;
  return (
    <div className="space-y-4">
      <Link to="/mentoring" className="text-sm text-indigo-600">Volver a mentoría</Link>
      <div className="card max-w-3xl space-y-4">
        <div className="flex flex-wrap gap-2">
          <span className="badge">{question.topic_name}</span>
          <LevelBadge level={question.level} />
        </div>
        <p className="text-lg font-medium">{question.text}</p>
        <ul className="space-y-2 text-sm">
          {question.choices.map((choice) => (
            <li key={choice.id} className={`rounded-lg border px-4 py-3 ${revealed && choice.is_correct ? "border-green-500 bg-green-50" : "border-slate-200"}`}>
              {choice.text}
            </li>
          ))}
        </ul>
        {revealed && question.explanation && <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{question.explanation}</p>}
        <QuestionTools question={question} />
      </div>
    </div>
  );
}
