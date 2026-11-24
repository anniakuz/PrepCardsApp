from rest_framework import serializers

MIN_QUESTIONS = 20
MAX_QUESTIONS = 300
MAX_ERRORS = 25

EXAMPLE = {
    "questions": [
        {
            "level": 1,
            "text": "¿Qué palabra clave declara una constante en JavaScript?",
            "choices": ["var", "let", "const", "static"],
            "answer": 2,
            "explanation": "const declara una variable que no se puede reasignar.",
        },
        {
            "level": 3,
            "text": "¿Qué devuelve typeof null?",
            "choices": ["null", "object", "undefined", "number"],
            "answer": 1,
            "explanation": "Es un error histórico del lenguaje que se mantiene por compatibilidad.",
        },
    ],
    "_instrucciones": (
        "Este archivo es solo un ejemplo con 2 preguntas. Hacen falta al menos 20. "
        "answer es la posición de la opción correcta empezando en 0. "
        "level es opcional (1 inicial, 5 experto), pero si lo pones, ponlo en todas. "
        "Cada pregunta lleva exactamente 4 opciones distintas."
    ),
}


def _text(value, limit):
    return str(value).strip() if isinstance(value, (str, int, float)) and not isinstance(value, bool) else ""


def parse_questions(data, minimum=MIN_QUESTIONS):
    """Valida y normaliza las preguntas de un archivo JSON.

    Acepta una lista de preguntas o un objeto con la clave "questions".
    Devuelve (preguntas, usa_niveles). Si algo falla lanza un error con la lista de problemas.
    """
    items = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise serializers.ValidationError({"questions": ["El archivo debe contener una lista de preguntas"]})

    errors = []
    if len(items) < minimum:
        errors.append(f"Hacen falta al menos {minimum} preguntas y el archivo tiene {len(items)}")
    if len(items) > MAX_QUESTIONS:
        errors.append(f"El máximo es {MAX_QUESTIONS} preguntas y el archivo tiene {len(items)}")

    parsed = []
    for position, item in enumerate(items[:MAX_QUESTIONS], start=1):
        if not isinstance(item, dict):
            errors.append(f"Pregunta {position}. Formato no válido")
            continue
        problems = []

        text = _text(item.get("text"), 1000)
        if not text:
            problems.append("falta el texto")
        elif len(text) > 1000:
            problems.append("el texto supera los 1000 caracteres")

        choices = item.get("choices")
        clean = []
        if not isinstance(choices, list) or len(choices) != 4:
            problems.append("debe tener exactamente 4 opciones")
        else:
            clean = [_text(choice, 300) for choice in choices]
            if not all(clean):
                problems.append("hay opciones vacías")
            elif len(set(clean)) != 4:
                problems.append("hay opciones repetidas")
            elif any(len(choice) > 300 for choice in clean):
                problems.append("una opción supera los 300 caracteres")

        answer = item.get("answer")
        if isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer <= 3:
            problems.append("answer debe ser un número del 0 al 3")

        level = item.get("level")
        if level is not None and (isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 5):
            problems.append("level debe ser un número del 1 al 5")
            level = None

        explanation = _text(item.get("explanation"), 1500)
        if len(explanation) > 1500:
            problems.append("la explicación supera los 1500 caracteres")

        if problems:
            errors.append(f"Pregunta {position}. " + ", ".join(problems).capitalize())
            continue
        parsed.append({
            "text": text, "choices": clean, "answer": answer, "level": level, "explanation": explanation,
        })

    with_level = sum(1 for question in parsed if question["level"] is not None)
    if not errors and 0 < with_level < len(parsed):
        errors.append("Todas las preguntas deben tener level o ninguna")

    if errors:
        extra = len(errors) - MAX_ERRORS
        shown = errors[:MAX_ERRORS] + ([f"Y {extra} problemas más"] if extra > 0 else [])
        raise serializers.ValidationError({"questions": shown})
    return parsed, with_level > 0
