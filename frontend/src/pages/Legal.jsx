import { Link, Navigate, useParams } from "react-router-dom";

// Rellena estos datos antes de publicar la web.
const OWNER = {
  name: "[NOMBRE Y APELLIDOS DEL TITULAR]",
  id: "[NIF/DNI]",
  address: "[DOMICILIO]",
  email: "[EMAIL DE CONTACTO]",
};

const H = ({ children }) => <h2 className="mt-6 text-lg font-semibold">{children}</h2>;
const List = ({ items }) => <ul className="list-disc space-y-1 pl-5">{items.map((i) => <li key={i}>{i}</li>)}</ul>;

function Aviso() {
  return (
    <>
      <p>En cumplimiento de la Ley 34/2002 de servicios de la sociedad de la información (LSSI-CE), se informa de lo siguiente.</p>
      <H>Titular</H>
      <List items={[`Titular. ${OWNER.name}`, `NIF. ${OWNER.id}`, `Domicilio. ${OWNER.address}`, `Contacto. ${OWNER.email}`]} />
      <H>Actividad</H>
      <p>PrepCards es una plataforma educativa para practicar preguntas de entrevistas técnicas de programación. Es un proyecto académico sin ánimo de lucro.</p>
      <H>Propiedad intelectual</H>
      <p>El código y el diseño de la plataforma pertenecen a su titular. Las preguntas de los temas creados por usuarios son responsabilidad de quien las crea, que garantiza que tiene derecho a compartirlas.</p>
      <H>Responsabilidad</H>
      <p>Las preguntas, las respuestas del chatbot y los análisis de ofertas pueden contener errores. Se ofrecen como ayuda para estudiar y no garantizan el resultado de ninguna entrevista.</p>
    </>
  );
}

function Privacidad() {
  return (
    <>
      <p>Esta política explica cómo se tratan tus datos personales conforme al Reglamento General de Protección de Datos (RGPD) y la Ley Orgánica 3/2018 (LOPDGDD).</p>
      <H>Responsable</H>
      <p>{OWNER.name}, {OWNER.id}, {OWNER.address}. Contacto. {OWNER.email}</p>
      <H>Datos que tratamos</H>
      <List items={[
        "Cuenta. Usuario, email y contraseña (guardada cifrada).",
        "Perfil. Edad, sexo, experiencia y el texto de Sobre mí, si lo escribes.",
        "Uso. Respuestas, nivel por tema, preguntas guardadas y rondas.",
        "Comunicaciones. Mensajes con tu mentor y con el chatbot.",
        "Contenido. Ofertas de trabajo que pegas y los temas que creas.",
        "Aceptación de los términos. Fecha y versión.",
      ]} />
      <H>Para qué y con qué base legal</H>
      <List items={[
        "Prestarte el servicio, incluidos el registro, la práctica, los niveles y la mentoría. Base. Ejecución del servicio que aceptas al registrarte.",
        "Enviarte el email de bienvenida, la recuperación de contraseña y avisos de práctica. Base. Ejecución del servicio.",
        "Mantener la seguridad y evitar abusos. Base. Interés legítimo.",
      ]} />
      <H>Con quién compartimos datos</H>
      <List items={[
        "Tu mentor ve tus estadísticas y respuestas solo si lo activas tú en Mentoría. Puedes desactivarlo cuando quieras.",
        "Anthropic, proveedor de inteligencia artificial. Recibe el texto de las ofertas que analizas, las preguntas de los temas que pides publicar y tus mensajes al chatbot. No se le envía tu email ni tu nombre de usuario. Puede tratar los datos en Estados Unidos con las garantías previstas por el RGPD.",
        "El proveedor de alojamiento y el de correo electrónico, como encargados del tratamiento.",
        "Los temas públicos, con su nombre de creador, son visibles para todos los usuarios.",
      ]} />
      <p className="mt-2">No pegues en las ofertas ni en el chatbot datos personales de otras personas.</p>
      <H>Cuánto tiempo los conservamos</H>
      <p>Mientras tengas la cuenta. Al eliminarla desde Mi perfil se borran tus datos, tus respuestas y tus temas privados.</p>
      <H>Tus derechos</H>
      <p>Puedes ejercer los derechos de acceso, rectificación, supresión, oposición, limitación y portabilidad. Desde Mi perfil puedes editar tus datos, descargarlos en JSON y eliminar tu cuenta. También puedes escribir a {OWNER.email}. Si crees que no hemos atendido tus derechos, puedes reclamar ante la Agencia Española de Protección de Datos (www.aepd.es).</p>
      <H>Menores</H>
      <p>Hay que tener al menos 14 años para registrarse, que es la edad de consentimiento en España.</p>
    </>
  );
}

function Cookies() {
  return (
    <>
      <p>PrepCards no usa cookies de publicidad ni de analítica. Solo usa almacenamiento técnico del navegador, imprescindible para que el servicio funcione. Según la LSSI-CE y la guía de la AEPD, este tipo de almacenamiento no necesita tu consentimiento, pero te informamos de él.</p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-slate-500">
            <tr><th className="py-2 pr-3">Nombre</th><th className="pr-3">Finalidad</th><th className="pr-3">Duración</th><th>Tipo</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            <tr><td className="py-2 pr-3 font-mono">access, refresh</td><td className="pr-3">Mantener tu sesión iniciada</td><td className="pr-3">Hasta que cierras sesión</td><td>Técnica, propia</td></tr>
            <tr><td className="py-2 pr-3 font-mono">cookie_notice</td><td className="pr-3">Recordar que has visto este aviso</td><td className="pr-3">Hasta que lo borras</td><td>Técnica, propia</td></tr>
          </tbody>
        </table>
      </div>
      <H>Cómo borrarlas</H>
      <p>Cierra sesión para eliminar los datos de sesión. También puedes borrar los datos del sitio desde los ajustes de tu navegador.</p>
      <p className="mt-2">Si en el futuro se añadiera analítica o cualquier cookie no técnica, se pedirá antes tu consentimiento con la opción de rechazarla.</p>
    </>
  );
}

function Terminos() {
  return (
    <>
      <p>Al registrarte aceptas estos términos de uso.</p>
      <H>Uso del servicio</H>
      <List items={[
        "Debes tener al menos 14 años y dar datos verdaderos.",
        "Eres responsable de tu contraseña y de lo que se haga con tu cuenta.",
        "No uses la plataforma para fines ilícitos ni intentes acceder a datos de otros usuarios.",
      ]} />
      <H>Contenido de los usuarios</H>
      <List items={[
        "Eres responsable de las preguntas que subes. No subas contenido protegido por derechos de autor ajeno, ofensivo o ilegal.",
        "Al publicar un tema, autorizas que otros usuarios lo practiquen. Puedes volver a hacerlo privado cuando quieras.",
        "Podemos retirar contenido que incumpla estos términos.",
      ]} />
      <H>Mentores</H>
      <p>Los mentores son usuarios y no empleados del titular. El titular no garantiza su formación ni el resultado de la mentoría. Un mentor solo accede a tus estadísticas y respuestas si tú lo autorizas.</p>
      <H>Inteligencia artificial</H>
      <p>El chatbot, el análisis de ofertas y la verificación de temas usan IA y pueden equivocarse. Contrasta lo importante. El chatbot tiene un límite diario de mensajes.</p>
      <H>Baja y cambios</H>
      <p>Puedes eliminar tu cuenta desde Mi perfil. Podemos modificar estos términos y, si cambian de forma relevante, se te pedirá aceptarlos de nuevo.</p>
      <H>Ley aplicable</H>
      <p>Se aplica la legislación española.</p>
    </>
  );
}

const PAGES = {
  aviso: ["Aviso legal", Aviso],
  privacidad: ["Política de privacidad", Privacidad],
  cookies: ["Política de cookies", Cookies],
  terminos: ["Términos de uso", Terminos],
};

export const LEGAL_LINKS = Object.entries(PAGES).map(([key, [title]]) => [key, title]);

export function LegalFooter() {
  return (
    <footer className="mt-auto border-t border-slate-200 bg-white px-4 py-4 text-center text-xs text-slate-500">
      <p>
        {LEGAL_LINKS.map(([key, title], i) => (
          <span key={key}>
            {i > 0 && " · "}
            <Link className="hover:text-indigo-600" to={`/legal/${key}`}>{title}</Link>
          </span>
        ))}
      </p>
      <p className="mt-2">
        <a
          href="https://github.com/anniakuz"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 hover:text-indigo-600"
        >
          <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" aria-hidden="true">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          Creado por anniakuz
        </a>
      </p>
    </footer>
  );
}

export default function Legal() {
  const { page } = useParams();
  const entry = PAGES[page];
  if (!entry) return <Navigate to="/legal/aviso" replace />;
  const [title, Body] = entry;
  return (
    <div className="flex min-h-screen flex-col">
      <div className="mx-auto max-w-3xl space-y-3 px-4 py-8 text-sm leading-relaxed text-slate-700">
        <Link to="/" className="text-indigo-600">Volver a PrepCards</Link>
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        <Body />
        <p className="pt-6 text-xs text-slate-400">Versión 2026-11</p>
      </div>
      <LegalFooter />
    </div>
  );
}
