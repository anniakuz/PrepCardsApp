import random

from django.db.models import Max, Q

from .models import Question, TopicProgress

MIN_LEVEL = 1
MAX_LEVEL = 5
START_LEVEL = 2
UP_STREAK = 5
DOWN_STREAK = 3
MIN_ROUND = 20
MAX_ROUND = 50

LEVEL_NAMES = {1: "Inicial", 2: "Básico", 3: "Intermedio", 4: "Avanzado", 5: "Experto"}


def get_progress(user, topic):
    progress, _ = TopicProgress.objects.get_or_create(
        user=user, topic=topic, defaults={"level": START_LEVEL, "max_level": START_LEVEL}
    )
    return progress


def apply_answer(progress, correct):
    """Aplica una respuesta a la racha. Cinco aciertos seguidos suben de nivel y tres fallos seguidos bajan.

    Devuelve "up", "down" o None. Cambiar de nivel reinicia las rachas.
    En el nivel 5 los aciertos no suben más y en el 1 los fallos no bajan más.
    """
    if correct:
        progress.correct_streak += 1
        progress.wrong_streak = 0
        if progress.correct_streak >= UP_STREAK:
            progress.correct_streak = 0
            if progress.level < MAX_LEVEL:
                progress.level += 1
                progress.max_level = max(progress.max_level, progress.level)
                return "up"
        return None
    progress.wrong_streak += 1
    progress.correct_streak = 0
    if progress.wrong_streak >= DOWN_STREAK:
        progress.wrong_streak = 0
        if progress.level > MIN_LEVEL:
            progress.level -= 1
            return "down"
    return None


def set_level(progress, level):
    """Fija el nivel de partida. Solo se usa antes de empezar el tema."""
    progress.level = level
    progress.correct_streak = 0
    progress.wrong_streak = 0
    progress.save()


def candidate_levels(level):
    """El nivel pedido primero y luego los más cercanos, con el inferior antes que el superior."""
    order = [level]
    for distance in range(1, MAX_LEVEL):
        for candidate in (level - distance, level + distance):
            if MIN_LEVEL <= candidate <= MAX_LEVEL:
                order.append(candidate)
    return order


def _choose(questions, user):
    """Prefiere preguntas que el usuario nunca ha respondido y después las respondidas hace más tiempo."""
    rows = list(
        questions.annotate(last=Max("reviews__created_at", filter=Q(reviews__user=user))).values_list("id", "last")
    )
    if not rows:
        return None
    fresh = [pk for pk, last in rows if last is None]
    if fresh:
        return random.choice(fresh)
    rows.sort(key=lambda row: row[1])
    return random.choice(rows[:5])[0]


def pick_question(user, topic, level, exclude_ids):
    """Id de la siguiente pregunta de la ronda, adaptada al nivel actual, o None si no quedan."""
    questions = Question.objects.filter(topic=topic).exclude(id__in=exclude_ids)
    if not topic.uses_levels:
        return _choose(questions, user)
    for candidate in candidate_levels(level):
        pk = _choose(questions.filter(level=candidate), user)
        if pk:
            return pk
    return _choose(questions.filter(level__isnull=True), user)
