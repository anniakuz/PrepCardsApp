import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from config.ai_client import AITemporaryError, AIUnavailable, retry_or_none

from . import ai
from .models import Review, Topic

logger = logging.getLogger("prepcards.tasks")
BATCH = 30


def _failed(topic, problem):
    """La IA no pudo responder (cuota, red, clave). No es un rechazo, se puede volver a intentar."""
    topic.visibility = "private"
    topic.publish_status = "error"
    topic.publish_report = [{"position": None, "question": "", "problem": problem}]
    topic.save(update_fields=["visibility", "publish_status", "publish_report"])


def _reject(topic, problem):
    topic.visibility = "private"
    topic.publish_status = "rejected"
    topic.publish_report = [{"position": None, "question": "", "problem": problem}]
    topic.save(update_fields=["visibility", "publish_status", "publish_report"])


@shared_task(bind=True, max_retries=3)
def verify_topic_task(self, topic_id):
    """La IA revisa todas las preguntas de un tema. Solo se publica si el 100% está bien."""
    topic = Topic.objects.filter(pk=topic_id).first()
    if not topic or topic.publish_status != "pending":
        return

    questions = list(topic.questions.prefetch_related("choices").order_by("id"))
    items = []
    for position, question in enumerate(questions, start=1):
        choices = list(question.choices.all())
        items.append({
            "index": position,
            "text": question.text,
            "choices": [choice.text for choice in choices],
            "answer": next((i for i, choice in enumerate(choices) if choice.is_correct), 0),
            "explanation": question.explanation,
        })

    issues = []
    try:
        for start in range(0, len(items), BATCH):
            batch = items[start:start + BATCH]
            verdicts = {result.get("index"): result for result in ai.verify_questions(batch)}
            for item in batch:
                verdict = verdicts.get(item["index"])
                if verdict is None:
                    problem = "La IA no devolvió veredicto para esta pregunta"
                elif not verdict.get("ok"):
                    problem = verdict.get("problem") or "La IA ha marcado un problema"
                else:
                    continue
                issues.append({"position": item["index"], "question": item["text"][:200], "problem": problem})
    except AITemporaryError as exc:
        retry = retry_or_none(self, exc)
        if retry:
            raise retry
        return _failed(topic, str(exc))
    except AIUnavailable as exc:
        return _failed(topic, str(exc))

    if issues:
        topic.visibility = "private"
        topic.publish_status = "rejected"
    else:
        topic.visibility = "public"
        topic.publish_status = "approved"
    topic.publish_report = issues
    topic.save(update_fields=["visibility", "publish_status", "publish_report"])
    logger.info("topic verified id=%s issues=%s", topic.pk, len(issues))


@shared_task
def send_practice_reminders():
    """Tarea periódica de Celery Beat. Avisa a quien practicó esta semana y hoy todavía no."""
    now = timezone.now()
    today = timezone.localdate()
    recent = set(Review.objects.filter(created_at__gte=now - timedelta(days=7)).values_list("user_id", flat=True))
    done_today = set(Review.objects.filter(created_at__date=today).values_list("user_id", flat=True))
    users = get_user_model().objects.filter(pk__in=recent - done_today, is_active=True).exclude(email="")
    sent = 0
    for user in users:
        send_mail(
            "Hoy todavía no has practicado en PrepCards",
            f"Hola {user.username}.\n\nUna ronda de 20 preguntas te lleva unos minutos.\n{settings.FRONTEND_URL}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        sent += 1
    logger.info("practice reminders sent=%s", sent)
    return sent
