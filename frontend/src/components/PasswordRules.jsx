export const PASSWORD_RULES = [
  ["Un mínimo de 10 caracteres", (p) => p.length >= 10],
  ["Una letra mayúscula", (p) => /[A-Z]/.test(p)],
  ["Una letra minúscula", (p) => /[a-z]/.test(p)],
  ["Un número", (p) => /\d/.test(p)],
  ["Un carácter especial (Ex: # ? ! @ $ % ^ & * - _ .)", (p) => /[^A-Za-z0-9\s]/.test(p)],
];

export const passwordIsValid = (password) => PASSWORD_RULES.every(([, test]) => test(password));

export default function PasswordRules({ password }) {
  return (
    <ul className="space-y-1 rounded-xl border border-slate-200 bg-slate-50/80 p-3 text-sm">
      {PASSWORD_RULES.map(([label, test]) => {
        const ok = test(password);
        return (
          <li key={label} className={`flex items-center gap-2 transition-colors ${ok ? "text-green-700" : "text-slate-500"}`}>
            <span className={`inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] text-white transition-colors ${ok ? "bg-green-600" : "bg-slate-300"}`}>
              {ok ? "✓" : ""}
            </span>
            {label}
          </li>
        );
      })}
    </ul>
  );
}
