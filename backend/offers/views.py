import random

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import get_profile

from . import ai
from .models import JobOffer, OfferAnswer, OfferAttempt
from .serializers import OfferSerializer
from .services import finish_attempt, plan, valid_counts
from .tasks import analyze_offer_task, generate_questions_task

NO_KEY = {"detail": "Falta configurar la clave de IA (GEMINI_API_KEY o ANTHROPIC_API_KEY) en el archivo .env"}


def attempt_payload(attempt):
    """Estado de un intento. Nunca incluye el nivel de las preguntas ni la respuesta correcta."""
    total = len(attempt.order)
    answered = attempt.answers.count()
    question = None
    if attempt.status == "active" and answered < total:
        from quiz.models import Question

        current = Question.objects.prefetch_related("choices").get(pk=attempt.order[answered])
        question = {
            "id": current.id, "text": current.text,
            "choices": [{"id": c.id, "text": c.text} for c in current.choices.all()],
        }
    finished = attempt.status == "finished"
    return {
        "id": attempt.id, "status": attempt.status, "total": total, "answered": answered,
        "question": question, "result": attempt.result if finished else None,
        "review": attempt_review(attempt) if finished else [],
    }


def attempt_review(attempt):
    """Preguntas contestadas con la respuesta elegida y la correcta. Solo cuando el cuestionario ha terminado."""
    answers = attempt.answers.select_related("question").prefetch_related("question__choices")
    by_question = {a.question_id: a for a in answers}
    review = []
    for question_id in attempt.order:
        answer = by_question.get(question_id)
        if not answer:
            continue
        question = answer.question
        review.append({
            "id": question.id, "text": question.text, "requirement": question.requirement,
            "explanation": question.explanation, "correct": answer.correct, "chosen": answer.choice_id,
            "choices": [{"id": c.id, "text": c.text, "is_correct": c.is_correct} for c in question.choices.all()],
        })
    return review


class OfferViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Ofertas de trabajo y su cuestionario. El análisis y la generación se ejecutan en segundo plano con Celery.

    El cliente consulta el detalle de la oferta hasta que status y generation_status dejan de estar en curso.
    """

    serializer_class = OfferSerializer

    def get_queryset(self):
        return JobOffer.objects.filter(user=self.request.user)

    def create(self, request):
        if get_profile(request.user).role == "mentor":
            return Response({"detail": "Los mentores no hacen cuestionarios de oferta"}, status=status.HTTP_403_FORBIDDEN)
        raw_text = (request.data.get("raw_text") or "").strip()
        if not raw_text:
            return Response({"detail": "Pega el texto de la oferta"}, status=status.HTTP_400_BAD_REQUEST)
        if not ai.is_configured():
            return Response(NO_KEY, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        offer = JobOffer.objects.create(user=request.user, raw_text=raw_text, status="pending")
        analyze_offer_task.delay(offer.id)
        offer.refresh_from_db()
        return Response(OfferSerializer(offer, context={"request": request}).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """Crea el cuestionario con los requisitos elegidos. Sustituye el anterior y sus resultados."""
        offer = self.get_object()
        if offer.status != "ready":
            return Response({"detail": "La oferta todavía no está analizada"}, status=status.HTTP_409_CONFLICT)
        if offer.generation_status == "running":
            return Response({"detail": "Ya hay una generación en curso"}, status=status.HTTP_409_CONFLICT)
        valid = {r["name"] for r in offer.requirements}
        selected = [n for n in (request.data.get("requirements") or []) if n in valid]
        if not selected:
            return Response({"detail": "Elige al menos un requisito"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            count = int(request.data.get("count") or 20)
        except (TypeError, ValueError):
            count = 20
        if count not in valid_counts(len(selected)):
            return Response(
                {"detail": "Puedes hacer 20 preguntas, o 40 si evalúas más de tres requisitos"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if plan(offer, selected, count)["needs"] and not ai.is_configured():
            return Response(NO_KEY, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        offer.generation_status = "running"
        offer.generation_error = ""
        offer.save(update_fields=["generation_status", "generation_error"])
        generate_questions_task.delay(offer.id, selected, count)
        offer.refresh_from_db()
        return Response(OfferSerializer(offer, context={"request": request}).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="attempts")
    def start_attempt(self, request, pk=None):
        offer = self.get_object()
        active = offer.attempts.filter(user=request.user, status="active").first()
        if active:
            return Response(attempt_payload(active))
        ids = list(offer.questions.values_list("id", flat=True))
        if not ids:
            return Response({"detail": "La oferta todavía no tiene cuestionario"}, status=status.HTTP_409_CONFLICT)
        random.shuffle(ids)
        attempt = OfferAttempt.objects.create(offer=offer, user=request.user, order=ids)
        return Response(attempt_payload(attempt), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path=r"attempts/(?P<attempt_id>[0-9]+)")
    def attempt_detail(self, request, pk=None, attempt_id=None):
        offer = self.get_object()
        attempt = offer.attempts.filter(user=request.user, pk=attempt_id).first()
        if not attempt:
            return Response({"detail": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return Response(attempt_payload(attempt))

    @action(detail=True, methods=["post"], url_path=r"attempts/(?P<attempt_id>[0-9]+)/answer")
    def answer_attempt(self, request, pk=None, attempt_id=None):
        offer = self.get_object()
        attempt = offer.attempts.filter(user=request.user, pk=attempt_id).first()
        if not attempt:
            return Response({"detail": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
        if attempt.status != "active":
            return Response({"detail": "Este cuestionario ya está terminado"}, status=status.HTTP_409_CONFLICT)
        answered = attempt.answers.count()
        question = offer.questions.prefetch_related("choices").get(pk=attempt.order[answered])
        choice = next((c for c in question.choices.all() if str(c.id) == str(request.data.get("choice"))), None)
        if choice is None:
            return Response({"detail": "Esa opción no es de esta pregunta"}, status=status.HTTP_400_BAD_REQUEST)
        OfferAnswer.objects.create(
            attempt=attempt, question=question, choice=choice, correct=choice.is_correct,
            requirement=question.requirement,
        )
        if answered + 1 >= len(attempt.order):
            finish_attempt(offer, attempt)
        return Response(attempt_payload(attempt))
