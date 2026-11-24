import axios from "axios";

const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const refresh = localStorage.getItem("refresh");
    const isTokenCall = original?.url?.includes("/auth/token");
    if (error.response?.status === 401 && refresh && !original._retry && !isTokenCall) {
      original._retry = true;
      try {
        const { data } = await axios.post("/api/auth/token/refresh/", { refresh });
        localStorage.setItem("access", data.access);
        return api(original);
      } catch {
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export function errorText(error) {
  const data = error.response?.data;
  if (!data) return "No se pudo conectar con el servidor";
  if (typeof data === "string") return "Error del servidor";
  if (data.detail) return data.detail;
  return Object.entries(data)
    .map(([field, messages]) => `${field} ${[].concat(messages).map(flatten).join(" ")}`)
    .join(". ");
}

function flatten(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(flatten).join(" ");
  if (value && typeof value === "object") return Object.values(value).map(flatten).join(" ");
  return String(value);
}

export function chatSocketUrl(enrollmentId) {
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const token = localStorage.getItem("access") || "";
  return `${scheme}://${window.location.host}/ws/chat/${enrollmentId}/?token=${token}`;
}

export const LEVEL_LABELS = { 1: "Inicial", 2: "Básico", 3: "Intermedio", 4: "Avanzado", 5: "Experto" };
export const ROLE_LABELS = { student: "Estudiante", mentor: "Mentor", admin: "Administrador" };
export const SEX_OPTIONS = [
  ["female", "Mujer"],
  ["male", "Hombre"],
  ["other", "Otro"],
  ["undisclosed", "Prefiero no decirlo"],
];
export const EXPERIENCE_OPTIONS = [
  ["none", "Sin experiencia"],
  ["6m", "6 meses"],
  ["1y", "1 año"],
  ["2y", "2 años"],
  ["3y", "3 años"],
  ["4y", "4 años"],
  ["5plus", "5 años o más"],
];

export function downloadExample() {
  return api.get("/topics/example/", { responseType: "blob" }).then(({ data }) => {
    const url = URL.createObjectURL(data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ejemplo-tema.json";
    link.click();
    URL.revokeObjectURL(url);
  });
}

export default api;
