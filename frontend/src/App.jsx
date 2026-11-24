import { useCallback, useEffect, useState } from "react";
import { Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import api from "./api.js";
import { useAuth } from "./auth.jsx";
import CookieNotice from "./components/CookieNotice.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import Legal, { LegalFooter } from "./pages/Legal.jsx";
import CreateTopic from "./pages/CreateTopic.jsx";
import MentorChat from "./pages/MentorChat.jsx";
import Mentoring from "./pages/Mentoring.jsx";
import MyTopics from "./pages/MyTopics.jsx";
import OfferDetail from "./pages/OfferDetail.jsx";
import OfferQuiz from "./pages/OfferQuiz.jsx";
import Offers from "./pages/Offers.jsx";
import { ForgotPassword, ResetPassword } from "./pages/PasswordReset.jsx";
import Practice from "./pages/Practice.jsx";
import Profile from "./pages/Profile.jsx";
import QuestionView from "./pages/QuestionView.jsx";
import Stats from "./pages/Stats.jsx";
import Topics from "./pages/Topics.jsx";

const MENTOR_NAV = [
  { to: "/mentoring", label: "Mis estudiantes" },
  { to: "/create", label: "Crear mi cuestionario" },
  { to: "/stats", label: "Estadísticas" },
  { to: "/profile", label: "Mi perfil" },
];

const NAV = [
  { to: "/topics", label: "Temas" },
  { to: "/my-topics", label: "Mi biblioteca" },
  { to: "/mentoring", label: "Mentoría" },
  { to: "/offers", label: "Análisis de oferta" },
  { to: "/create", label: "Crear mi cuestionario" },
  { to: "/stats", label: "Estadísticas" },
  { to: "/profile", label: "Mi perfil" },
];

function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  function toggle() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch (e) {}
    setDark(next);
  }
  return [dark, toggle];
}

const NO_NOTES = { total: 0, pending_requests: 0, unread: {}, unread_messages: 0 };

function Layout() {
  const { user, loading, logout } = useAuth();
  const [notes, setNotes] = useState(NO_NOTES);
  const [dark, toggleTheme] = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);

  const refreshNotes = useCallback(() => {
    api.get("/mentoring/notifications/").then(({ data }) => setNotes(data)).catch(() => {});
  }, []);

  // Los avisos de mentoría se consultan cada 20 segundos
  useEffect(() => {
    if (!user) return;
    refreshNotes();
    const timer = setInterval(refreshNotes, 20000);
    return () => clearInterval(timer);
  }, [user, refreshNotes]);

  if (loading) return <p className="p-8 text-center text-slate-500">Cargando</p>;
  if (!user) return <Navigate to="/login" replace />;

  const linkClass = ({ isActive }) =>
    `rounded-xl px-3 py-1.5 text-sm font-medium transition ${
      isActive ? "bg-indigo-100 text-indigo-700 shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
    }`;

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-3">
          <span className="mr-4 bg-gradient-to-r from-indigo-600 to-fuchsia-500 bg-clip-text text-xl font-extrabold tracking-tight text-transparent">PrepCards</span>
          <button
            className="btn-secondary ml-auto !py-1.5 md:hidden"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-expanded={menuOpen}
            aria-label="Abrir o cerrar el menú"
          >
            {menuOpen ? "✕ Cerrar" : "☰ Menú"}
          </button>
          <nav className={`${menuOpen ? "flex" : "hidden"} w-full flex-col gap-1 md:order-none md:flex md:w-auto md:flex-1 md:flex-row md:flex-wrap`} onClick={() => setMenuOpen(false)}>
            {(user.role === "mentor" ? MENTOR_NAV : NAV).map((item) => (
              <NavLink key={item.to} to={item.to} className={linkClass}>
                {item.label}
                {item.to === "/mentoring" && notes.total > 0 && (
                  <span
                    className="ml-1.5 animate-pop rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white"
                    title={`${notes.pending_requests} solicitudes y ${notes.unread_messages} mensajes sin leer`}
                  >
                    {notes.total}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>
          <span className="hidden text-sm text-slate-500 sm:inline">{user.first_name || user.username}</span>
          <button
            onClick={toggleTheme}
            className="btn-secondary !py-1.5"
            title={dark ? "Cambiar a modo claro" : "Cambiar a modo noche"}
            aria-label={dark ? "Cambiar a modo claro" : "Cambiar a modo noche"}
          >
            {dark ? "☀ Claro" : "☾ Noche"}
          </button>
          <button onClick={logout} className="btn-secondary !py-1.5">Salir</button>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-3 py-6 sm:px-4 sm:py-8">
        <Outlet context={{ notes, refreshNotes }} />
      </main>
      <LegalFooter />
    </div>
  );
}

function Home() {
  const { user } = useAuth();
  return <Navigate to={user?.role === "mentor" ? "/mentoring" : "/my-topics"} replace />;
}

export default function App() {
  return (
    <>
    <CookieNotice />
    <Routes>
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route path="/legal/:page" element={<Legal />} />
      <Route path="/forgot" element={<ForgotPassword />} />
      <Route path="/reset/:uid/:token" element={<ResetPassword />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/topics" element={<Topics />} />
        <Route path="/my-topics" element={<MyTopics />} />
        <Route path="/practice/:topicId" element={<Practice />} />
        <Route path="/question/:id" element={<QuestionView />} />
        <Route path="/mentoring" element={<Mentoring />} />
        <Route path="/mentoring/:id" element={<MentorChat />} />
        <Route path="/offers" element={<Offers />} />
        <Route path="/offers/:id" element={<OfferDetail />} />
        <Route path="/offers/:id/quiz" element={<OfferQuiz />} />
        <Route path="/create" element={<CreateTopic />} />
        <Route path="/stats" element={<Stats />} />
        <Route path="/profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </>
  );
}
