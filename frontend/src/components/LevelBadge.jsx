import { LEVEL_LABELS } from "../api.js";

const COLORS = {
  1: "bg-emerald-100 text-emerald-700",
  2: "bg-lime-100 text-lime-700",
  3: "bg-amber-100 text-amber-700",
  4: "bg-orange-100 text-orange-700",
  5: "bg-rose-100 text-rose-700",
};

export default function LevelBadge({ level, prefix = "Nivel" }) {
  if (!level) return null;
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${COLORS[level]}`}>
      {prefix === null ? LEVEL_LABELS[level] : `${prefix} ${level} · ${LEVEL_LABELS[level]}`}
    </span>
  );
}
