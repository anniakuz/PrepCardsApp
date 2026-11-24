import * as SecureStore from "expo-secure-store";

// En un móvil real, localhost es el propio móvil. Pon aquí la IP de tu ordenador en la red local.
const API_URL = (process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000/api").replace(/\/$/, "");

let access = null;
let onSessionExpired = () => {};

export function setSessionExpiredHandler(handler) {
  onSessionExpired = handler;
}

export async function loadSession() {
  access = await SecureStore.getItemAsync("access");
  return Boolean(access);
}

async function saveTokens(tokens) {
  access = tokens.access;
  await SecureStore.setItemAsync("access", tokens.access);
  if (tokens.refresh) await SecureStore.setItemAsync("refresh", tokens.refresh);
}

async function clearTokens() {
  access = null;
  await SecureStore.deleteItemAsync("access");
  await SecureStore.deleteItemAsync("refresh");
}

async function refreshAccess() {
  const refresh = await SecureStore.getItemAsync("refresh");
  if (!refresh) return false;
  const response = await fetch(`${API_URL}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!response.ok) return false;
  await saveTokens(await response.json());
  return true;
}

function messageFrom(data) {
  if (!data) return "Error del servidor";
  if (data.detail) return data.detail;
  return Object.values(data).flat().join(" ");
}

export async function request(path, { method = "GET", body, auth = true } = {}) {
  const run = () =>
    fetch(`${API_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(auth && access ? { Authorization: `Bearer ${access}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

  let response;
  try {
    response = await run();
    if (response.status === 401 && auth) {
      if (await refreshAccess()) {
        response = await run();
      } else {
        await clearTokens();
        onSessionExpired();
        throw new Error("La sesión ha caducado");
      }
    }
  } catch (error) {
    if (error.message === "La sesión ha caducado") throw error;
    throw new Error(`No se pudo conectar con ${API_URL}`);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(messageFrom(data));
  return data;
}

export async function login(username, password) {
  const tokens = await request("/auth/token/", { method: "POST", body: { username, password }, auth: false });
  await saveTokens(tokens);
}

export async function logout() {
  const refresh = await SecureStore.getItemAsync("refresh");
  try {
    if (refresh) await request("/auth/logout/", { method: "POST", body: { refresh } });
  } catch {
    // el token ya no era válido
  }
  await clearTokens();
}

export const LEVEL_LABELS = { 1: "Inicial", 2: "Básico", 3: "Intermedio", 4: "Avanzado", 5: "Experto" };

// ws://host/ws/chat/<id>/?token=<jwt>. Se renueva el token antes de conectar.
export async function chatUrl(enrollmentId) {
  await request("/auth/me/");
  return `${API_URL.replace(/^http/, "ws").replace(/\/api$/, "")}/ws/chat/${enrollmentId}/?token=${access}`;
}
