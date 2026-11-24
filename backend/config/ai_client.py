import json
import urllib.error
import urllib.request

import anthropic
from django.conf import settings

MAX_RETRIES = 3
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
NO_KEY_MESSAGE = "Falta configurar la clave de IA (GEMINI_API_KEY o ANTHROPIC_API_KEY) en el archivo .env"


class AIUnavailable(Exception):
    """Error definitivo. Reintentar no lo arregla (falta la clave, petición no válida)."""


class AITemporaryError(AIUnavailable):
    """Error pasajero (red, límite de peticiones, fallo del servidor). Se puede reintentar."""


def provider():
    """Proveedor activo. AI_PROVIDER manda; si está vacío se usa el que tenga clave."""
    chosen = (settings.AI_PROVIDER or "").lower()
    if chosen in ("gemini", "anthropic"):
        return chosen
    if settings.GEMINI_API_KEY:
        return "gemini"
    return "anthropic"


def is_configured():
    key = settings.GEMINI_API_KEY if provider() == "gemini" else settings.ANTHROPIC_API_KEY
    return bool(key)


# Claude

def _claude_create(**kwargs):
    if not settings.ANTHROPIC_API_KEY:
        raise AIUnavailable(NO_KEY_MESSAGE)
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return client.messages.create(model=settings.ANTHROPIC_MODEL, **kwargs)
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError) as exc:
        raise AITemporaryError(f"La API de Claude no responde. {exc}") from exc
    except anthropic.APIError as exc:
        raise AIUnavailable(f"Error al llamar a la API de Claude. {exc}") from exc


# Gemini

def _gemini_generate(system, contents, max_tokens, schema=None):
    if not settings.GEMINI_API_KEY:
        raise AIUnavailable(NO_KEY_MESSAGE)
    config = {"maxOutputTokens": max_tokens}
    if schema is not None:
        config["responseMimeType"] = "application/json"
        config["responseJsonSchema"] = schema
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents, "generationConfig": config}
    request = urllib.request.Request(
        GEMINI_URL.format(model=settings.GEMINI_MODEL),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": settings.GEMINI_API_KEY},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (429, 500, 502, 503, 504):
            raise AITemporaryError(f"La API de Gemini no responde ({exc.code}).") from exc
        hint = " Comprueba GEMINI_MODEL, puede que el modelo ya no exista." if exc.code == 404 else ""
        if exc.code in (400, 403):
            hint = " Comprueba que GEMINI_API_KEY es correcta."
        raise AIUnavailable(f"Error al llamar a la API de Gemini ({exc.code}) con el modelo {settings.GEMINI_MODEL}.{hint}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise AITemporaryError(f"No se pudo conectar con Gemini. {exc}") from exc
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AIUnavailable("La respuesta de Gemini no contiene datos") from exc


def _gemini_contents(messages):
    return [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages
    ]


# Interfaz común

def call_tool(system, user, tool, max_tokens):
    """Pide una respuesta estructurada. tool es un esquema con name y input_schema."""
    if provider() == "gemini":
        text = _gemini_generate(system, _gemini_contents([{"role": "user", "content": user}]), max_tokens, tool["input_schema"])
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AITemporaryError("Gemini devolvió un JSON no válido") from exc
    message = _claude_create(
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
    )
    for block in message.content:
        if block.type == "tool_use":
            return block.input
    raise AIUnavailable("La respuesta del modelo no contiene datos")


def call_text(system, messages, max_tokens):
    """Conversación de texto libre. messages es una lista de {role, content}."""
    if provider() == "gemini":
        text = _gemini_generate(system, _gemini_contents(messages), max_tokens)
    else:
        message = _claude_create(max_tokens=max_tokens, system=system, messages=messages)
        text = "".join(block.text for block in message.content if block.type == "text").strip()
    if not text:
        raise AIUnavailable("La respuesta del modelo está vacía")
    return text


def retry_or_none(task, exc):
    """Devuelve la excepción Retry de Celery si quedan intentos. Si no, None."""
    if task.request.retries < MAX_RETRIES and not task.request.is_eager:
        return task.retry(exc=exc, countdown=20 * 2 ** task.request.retries)
    return None
