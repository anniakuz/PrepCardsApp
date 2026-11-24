import random

from django.db import transaction
from django.utils import timezone

from quiz.models import Choice, Question, Topic

from . import ai

MIN_QUESTIONS = 20
MAX_QUESTIONS = 50
REQUIRED_WEIGHT = 0.9
DEFAULT_LEVEL = 3
# Porcentaje de aciertos que hace falta en un requisito según el nivel que pide la oferta
THRESHOLDS = {1: 0.5, 2: 0.5, 3: 0.6, 4: 0.7, 5: 0.8}

# Si la IA no indica el tema oficial, se busca por palabras del nombre del requisito
ALIASES = {
    "java": ["java"],
    "python": ["python", "django", "flask", "fastapi"],
    "react": ["react", "reactjs", "react native"],
    "html-css": ["html", "html5", "css", "css3", "sass", "tailwind", "bootstrap"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "mariadb", "oracle"],
    "linux": ["linux", "unix", "bash", "shell"],
    "patrones-de-diseno": ["patrones de diseño", "design patterns", "solid", "patrones"],
    "aws-cloud": ["aws", "amazon web services", "cloud"],
}


def match_official(name, valid_slugs):
    """Devuelve el slug del tema oficial por alias, o cadena vacía."""
    words = name.lower()
    for slug, aliases in ALIASES.items():
        if slug in valid_slugs and any(a == words or f" {a} " in f" {words} " for a in aliases):
            return slug
    return ""


def clean_requirements(raw):
    valid = {slug for slug, _ in ai.official_topics()}
    result, seen = [], set()
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()[:80]
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        official = item.get("official") if item.get("official") in valid else match_official(name, valid)
        result.append({
            "name": name,
            "category": item.get("category") if item.get("category") in ai.CATEGORIES else "other",
            "importance": "nice_to_have" if item.get("importance") == "nice_to_have" else "required",
            "official": official,
        })
    return result


def clean_level(value):
    return value if isinstance(value, int) and 0 <= value <= 5 else 0


def quiz_level(offer):
    return offer.level or DEFAULT_LEVEL


def suggested_topics(offer):
    """Temas oficiales que cubren los requisitos de la oferta."""
    slugs = sorted({r.get("official") for r in offer.requirements if r.get("official")})
    return list(Topic.objects.filter(owner__isnull=True, slug__in=slugs).order_by("name"))


def valid_counts(selected_count):
    """20 preguntas siempre y 40 solo si se evalúan más de tres requisitos."""
    return (20, 40) if selected_count > 3 else (20,)


def plan(offer, selected, count=MIN_QUESTIONS):
    """Elige preguntas oficiales para los requisitos con tema oficial y calcula cuántas pide a la IA para el resto."""
    requirements = [r for r in offer.requirements if r["name"] in selected]
    base, extra = divmod(count, max(1, len(requirements)))
    target = quiz_level(offer)
    picks, needs, used = [], {}, set()
    for index, req in enumerate(requirements):
        per = base + (1 if index < extra else 0)
        taken = 0
        if req.get("official"):
            pool = [
                q for q in Question.objects.filter(topic__owner__isnull=True, topic__slug=req["official"])
                .prefetch_related("choices")
                if q.id not in used
            ]
            random.shuffle(pool)
            pool.sort(key=lambda q: abs((q.level or target) - target))
            for source in pool[:per]:
                used.add(source.id)
                picks.append((req["name"], source))
                taken += 1
        if taken < per:
            needs[req["name"]] = per - taken
    return {"picks": picks, "needs": needs}


@transaction.atomic
def save_offer_questions(offer, picks, items, language):
    """Sustituye el cuestionario de la oferta. Las preguntas no pertenecen a ningún tema."""
    offer.questions.all().delete()
    offer.attempts.all().delete()
    seen, created = set(), 0
    level = quiz_level(offer)

    for requirement, source in picks:
        if source.text in seen:
            continue
        seen.add(source.text)
        question = Question.objects.create(
            topic=None, requirement=requirement, level=source.level or level, text=source.text,
            explanation=source.explanation, language=source.language, job_offer=offer,
        )
        Choice.objects.bulk_create(
            Choice(question=question, text=c.text, is_correct=c.is_correct) for c in source.choices.all()
        )
        created += 1

    names = [r["name"] for r in offer.requirements]
    for item in items or []:
        if not isinstance(item, dict):
            continue
        choices = item.get("choices")
        index = item.get("correct_index")
        text = str(item.get("text") or "").strip()
        if not text or text in seen or not isinstance(choices, list) or len(choices) != 4:
            continue
        if not isinstance(index, int) or not 0 <= index < 4:
            continue
        requirement = item.get("requirement") if item.get("requirement") in names else ""
        if not requirement:
            continue
        seen.add(text)
        question = Question.objects.create(
            topic=None, requirement=requirement, level=level, text=text,
            explanation=str(item.get("explanation") or ""), language=language, job_offer=offer,
        )
        Choice.objects.bulk_create(
            Choice(question=question, text=str(c), is_correct=(i == index)) for i, c in enumerate(choices)
        )
        created += 1
    return created


def compatibility_score(required_scores, optional_scores):
    """Los requisitos obligatorios pesan el 90% y los opcionales el 10%. Sin una de las dos clases, la otra pesa el 100%."""
    def average(values):
        return sum(values) / len(values)

    if required_scores and optional_scores:
        return REQUIRED_WEIGHT * average(required_scores) + (1 - REQUIRED_WEIGHT) * average(optional_scores)
    return average(required_scores or optional_scores or [0.0])


def recommended_topics(offer, result):
    """Temas oficiales de los requisitos de la oferta. Marca los que conviene reforzar."""
    unmet = {r["name"] for r in result["requirements"] if not r["met"]}
    found = {}
    for req in offer.requirements:
        slug = req.get("official")
        if slug:
            item = found.setdefault(slug, {"requirements": [], "reinforce": False})
            item["requirements"].append(req["name"])
            item["reinforce"] = item["reinforce"] or req["name"] in unmet
    topics = Topic.objects.filter(owner__isnull=True, slug__in=found).order_by("name")
    ordered = sorted(topics, key=lambda t: (not found[t.slug]["reinforce"], t.name))
    return [
        {"id": t.id, "name": t.name, "slug": t.slug, **found[t.slug]} for t in ordered
    ]


def compute_result(offer, attempt):
    """Aciertos por requisito, porcentaje de compatibilidad y si se cumplen los requisitos obligatorios."""
    level = quiz_level(offer)
    threshold = THRESHOLDS[level]
    stats = {}
    for answer in attempt.answers.all():
        item = stats.setdefault(answer.requirement, {"answered": 0, "correct": 0})
        item["answered"] += 1
        item["correct"] += int(answer.correct)

    rows, required_scores, optional_scores, missing = [], [], [], []
    for req in offer.requirements:
        item = stats.get(req["name"], {"answered": 0, "correct": 0})
        evaluated = item["answered"] > 0
        score = item["correct"] / item["answered"] if evaluated else 0.0
        met = evaluated and score >= threshold
        if req["importance"] == "required":
            required_scores.append(score)
            if not met:
                missing.append(req["name"])
        else:
            optional_scores.append(score)
        rows.append({
            "name": req["name"], "importance": req["importance"], "evaluated": evaluated,
            "correct": item["correct"], "answered": item["answered"], "score": round(score * 100), "met": met,
        })

    total = sum(i["answered"] for i in stats.values())
    correct = sum(i["correct"] for i in stats.values())
    compatibility = round(100 * compatibility_score(required_scores, optional_scores))
    if not missing:
        verdict = "compatible"
    elif compatibility >= 50:
        verdict = "partial"
    else:
        verdict = "not_compatible"
    return {
        "total": total, "correct": correct, "accuracy": round(100 * correct / total) if total else 0,
        "compatibility": compatibility, "verdict": verdict, "missing_required": missing, "requirements": rows,
    }


def finish_attempt(offer, attempt):
    result = compute_result(offer, attempt)
    topics = recommended_topics(offer, result)
    result["recommended_topics"] = topics
    # Los temas recomendados no se guardan solos. El alumno decide si los añade a su biblioteca
    attempt.result = result
    attempt.status = "finished"
    attempt.finished_at = timezone.now()
    attempt.save(update_fields=["result", "status", "finished_at"])
