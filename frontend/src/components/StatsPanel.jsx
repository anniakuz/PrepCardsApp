import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import LevelBadge from "./LevelBadge.jsx";

const percent = (correct, total) => (total ? `${Math.round((correct / total) * 100)}%` : "sin datos");

export default function StatsPanel({ stats }) {
  const daily = stats.days.map((d) => ({ day: d.date.slice(5), Aciertos: d.correct, Fallos: d.total - d.correct }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="card">
          <p className="text-sm text-slate-500">Respuestas totales</p>
          <p className="text-4xl font-bold">{stats.total}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Tasa de acierto</p>
          <p className="text-4xl font-bold">{percent(stats.correct, stats.total)}</p>
        </div>
      </div>

      {stats.topics.some((t) => t.uses_levels && t.level) && (
        <div className="card space-y-3">
          <h2 className="text-lg font-semibold">Tu nivel por aptitud</h2>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {stats.topics.filter((t) => t.uses_levels && t.level).map((t) => (
              <div key={t.id} className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white/70 px-4 py-3">
                <span className="font-medium">{t.name}</span>
                <LevelBadge level={t.level} prefix={null} />
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2 className="mb-4 text-lg font-semibold">Actividad de los últimos 14 días</h2>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" fontSize={12} />
              <YAxis allowDecimals={false} fontSize={12} />
              <Tooltip />
              <Bar dataKey="Aciertos" stackId="a" fill="#6366f1" />
              <Bar dataKey="Fallos" stackId="a" fill="#fca5a5" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Nivel por tema</h2>
        {stats.topics.length === 0 && <p className="text-sm text-slate-500">Todavía no has respondido ninguna pregunta.</p>}
        {stats.topics.map((topic) => (
          <div key={topic.id} className="card space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold">{topic.name}</p>
              <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
                <span>{topic.total} respuestas</span>
                <span>Acierto {percent(topic.correct, topic.total)}</span>
              </div>
            </div>
            {topic.uses_levels ? (
              <>
                <div className="flex flex-wrap gap-2">
                  <LevelBadge level={topic.level} prefix="Nivel actual" />
                  <LevelBadge level={topic.max_level} prefix="Máximo alcanzado" />
                </div>
                {topic.evolution.length > 1 && (
                  <div className="h-28">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={topic.evolution.map((level, i) => ({ n: i + 1, Nivel: level }))}>
                        <XAxis dataKey="n" fontSize={11} />
                        <YAxis domain={[1, 5]} ticks={[1, 2, 3, 4, 5]} fontSize={11} width={24} />
                        <Tooltip />
                        <Line type="stepAfter" dataKey="Nivel" stroke="#6366f1" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
                <p className="text-xs text-slate-400">Evolución del nivel en tus últimas respuestas.</p>
              </>
            ) : (
              <p className="text-sm text-slate-500">Este tema no usa niveles.</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
