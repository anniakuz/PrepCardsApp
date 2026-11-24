import json
import logging
from datetime import timedelta

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings

from accounts.models import get_profile, role_of
from config.ai_client import AIUnavailable, is_configured

from . import ai
from .access import accessible_topics, can_access_question, can_manage_topic
from .cache import STATS_TTL, bump_stats, stats_key
from .importer import EXAMPLE, parse_questions
from .levels import MAX_ROUND, MIN_ROUND, apply_answer, get_progress, pick_question, set_level
from .models import AssistantMessage, Question, Review, Round, SavedQuestion, Topic
from .pagination import StandardPagination
from .serializers import (
    AssistantMessageSerializer,
    QuestionDetailSerializer,
    QuestionSerializer,
    TopicSerializer,
)
from .services import create_topic, replace_questions, request_publication
from .stats import build_stats

logger = logging.getLogger("prepcards")
MAX_FILE = 2 * 1024 * 1024


def topic_queryset(user):
    return (
        accessible_topics(user)
        .select_related("owner")
        .annotate(question_count=Count("questions", distinct=True), learners=Count("profiles", distinct=True))
    )


def my_topic_ids(user):
    return set(get_profile(user).topics.values_list("id", flat=True))


def read_questions(request):
    """Devuelve los datos del JSON, sea un archivo subido (campo file) o el campo questions."""
    upload = request.FILES.get("file")
    if upload:
        if upload.size > MAX_FILE:
            raise ValidationError({"file": ["El archivo supera los 2 MB"]})
        try:
            return json.loads(upload.read().decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError):
            raise ValidationError({"file": ["El archivo no es un JSON válido"]})
    data = request.data.get("questions") if hasattr(request.data, "get") else None
    if data is None:
        raise ValidationError({"questions": ["Sube un archivo JSON con las preguntas"]})
    if isinstance(data, str):
        try:
            return json.loads(data)
        except ValueError:
            raise ValidationError({"questions": ["El texto no es un JSON válido"]})
    return data


def get_topic(user, pk):
    return get_object_or_404(topic_queryset(user), pk=pk)


class TopicListView(APIView):
    """GET catálogo con búsqueda y orden por popularidad. POST crea un tema propio desde un JSON."""

    def get(self, request):
        queryset = topic_queryset(request.user)
        search = request.query_params.get("q", "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(owner__username__icontains=search))
        queryset = queryset.filter(Q(question_count__gt=0))
        kind = request.query_params.get("kind")
        if kind == "official":
            queryset = queryset.filter(visibility="official")
        elif kind == "community":
            queryset = queryset.filter(visibility="public", publish_status="approved").exclude(owner=request.user)
        if request.query_params.get("ordering") == "popular":
            queryset = queryset.order_by("-learners", "name", "id")
        else:
            queryset = queryset.order_by("owner_id", "name", "id")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        context = {"request": request, "my_topic_ids": my_topic_ids(request.user)}
        return paginator.get_paginated_response(TopicSerializer(page, many=True, context=context).data)

    def post(self, request):
        name = str(request.data.get("name") or "").strip()
        if not name or len(name) > 80:
            raise ValidationError({"name": ["El nombre es obligatorio y tiene como máximo 80 caracteres"]})
        visibility = request.data.get("visibility", "private")
        if visibility not in ("private", "public"):
            raise ValidationError({"visibility": ["Debe ser private o public"]})
        language = "en" if request.data.get("language") == "en" else "es"
        parsed, uses_levels = parse_questions(read_questions(request))
        if visibility == "public" and not is_configured():
            return Response(
                {"detail": "Falta configurar la clave de IA. Sin ella no se pueden publicar temas"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        topic = create_topic(
            request.user, name, str(request.data.get("description") or "")[:500], parsed, uses_levels, language
        )
        if visibility == "public":
            request_publication(topic)
        topic = get_topic(request.user, topic.pk)
        context = {"request": request, "my_topic_ids": my_topic_ids(request.user)}
        return Response(TopicSerializer(topic, context=context).data, status=status.HTTP_201_CREATED)


class MyTopicsView(APIView):
    def get(self, request):
        ids = my_topic_ids(request.user)
        topics = topic_queryset(request.user).filter(Q(id__in=ids) | Q(owner=request.user)).order_by("name", "id")
        progress = {p.topic_id: p for p in request.user.topic_progress.all()}
        data = TopicSerializer(topics, many=True, context={"request": request, "my_topic_ids": ids}).data
        for item in data:
            current = progress.get(item["id"])
            item["level"] = current.level if current and item["uses_levels"] else None
        return Response(data)


class PopularTopicsView(APIView):
    def get(self, request):
        topics = (
            topic_queryset(request.user)
            .filter(visibility__in=("official", "public"), question_count__gt=0)
            .order_by("-learners", "name")[:6]
        )
        context = {"request": request, "my_topic_ids": my_topic_ids(request.user)}
        return Response(TopicSerializer(topics, many=True, context=context).data)


class ExampleView(APIView):
    def get(self, request):
        response = JsonResponse(EXAMPLE, json_dumps_params={"ensure_ascii": False, "indent": 2})
        response["Content-Disposition"] = 'attachment; filename="ejemplo-tema.json"'
        return response


class TopicDetailView(APIView):
    def get(self, request, pk):
        topic = get_topic(request.user, pk)
        context = {"request": request, "my_topic_ids": my_topic_ids(request.user)}
        return Response(TopicSerializer(topic, context=context).data)

    def patch(self, request, pk):
        topic = get_topic(request.user, pk)
        if not can_manage_topic(request.user, topic):
            raise PermissionDenied("Solo el creador puede editar el tema")
        if "name" in request.data:
            name = str(request.data["name"]).strip()
            if not name or len(name) > 80:
                raise ValidationError({"name": ["El nombre es obligatorio y tiene como máximo 80 caracteres"]})
            topic.name = name
        if "description" in request.data:
            topic.description = str(request.data["description"])[:500]
        topic.save()
        return Response(TopicSerializer(get_topic(request.user, pk), context={"request": request}).data)

    def delete(self, request, pk):
        topic = get_topic(request.user, pk)
        if not can_manage_topic(request.user, topic):
            raise PermissionDenied("Solo el creador puede borrar el tema")
        topic.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TopicJoinView(APIView):
    def post(self, request, pk):
        get_profile(request.user).topics.add(get_topic(request.user, pk))
        return Response({"joined": True})

    def delete(self, request, pk):
        get_profile(request.user).topics.remove(get_topic(request.user, pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class TopicQuestionsView(APIView):
    """PUT sustituye las preguntas del tema con un JSON nuevo."""

    def put(self, request, pk):
        topic = get_topic(request.user, pk)
        if topic.owner_id is None or not can_manage_topic(request.user, topic):
            raise PermissionDenied("Solo el creador puede cambiar las preguntas")
        parsed, uses_levels = parse_questions(read_questions(request))
        replace_questions(topic, parsed, uses_levels, "en" if request.data.get("language") == "en" else "es")
        return Response(TopicSerializer(get_topic(request.user, pk), context={"request": request}).data)


class TopicPublishView(APIView):
    """POST pide la publicación. La IA verifica todas las preguntas. DELETE vuelve el tema a privado."""

    def post(self, request, pk):
        topic = get_topic(request.user, pk)
        if topic.owner_id is None or not can_manage_topic(request.user, topic):
            raise PermissionDenied("Solo el creador puede publicar el tema")
        if topic.publish_status == "pending":
            return Response({"detail": "Ya se está verificando"}, status=status.HTTP_409_CONFLICT)
        if not is_configured():
            return Response(
                {"detail": "Falta configurar la clave de IA. Sin ella no se pueden publicar temas"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        request_publication(topic)
        return Response(
            TopicSerializer(get_topic(request.user, pk), context={"request": request}).data,
            status=status.HTTP_202_ACCEPTED,
        )

    def delete(self, request, pk):
        topic = get_topic(request.user, pk)
        if topic.owner_id is None or not can_manage_topic(request.user, topic):
            raise PermissionDenied("Solo el creador puede despublicar el tema")
        topic.visibility = "private"
        topic.publish_status = ""
        topic.publish_report = []
        topic.save()
        return Response(TopicSerializer(get_topic(request.user, pk), context={"request": request}).data)


class TopicLevelView(APIView):
    """GET nivel actual. PUT fija el nivel de partida, pero solo antes de empezar el tema.

    Una vez fijado, el nivel solo sube o baja al responder preguntas.
    """

    def get(self, request, pk):
        topic = get_topic(request.user, pk)
        progress = get_progress(request.user, topic)
        return Response({"level": progress.level, "max_level": progress.max_level, "fixed": progress.fixed})

    def put(self, request, pk):
        topic = get_topic(request.user, pk)
        if not topic.uses_levels:
            raise ValidationError({"level": ["Este tema no usa niveles"]})
        try:
            level = int(request.data.get("level"))
        except (TypeError, ValueError):
            level = 0
        if not 1 <= level <= 5:
            raise ValidationError({"level": ["El nivel debe ser un número del 1 al 5"]})
        progress = get_progress(request.user, topic)
        if progress.fixed:
            return Response(
                {"detail": "El nivel ya está fijado. Solo cambia al subir o bajar respondiendo preguntas"},
                status=status.HTTP_409_CONFLICT,
            )
        set_level(progress, level)
        return Response({"level": progress.level, "max_level": progress.max_level, "fixed": progress.fixed})


def round_data(round_obj, request, question=None):
    answered = round_obj.reviews.count()
    saved_ids = set(request.user.saved_questions.values_list("question_id", flat=True))
    current = question or round_obj.current_question
    progress = get_progress(request.user, round_obj.topic)
    return {
        "id": round_obj.id,
        "topic": round_obj.topic_id,
        "topic_name": round_obj.topic.label,
        "uses_levels": round_obj.topic.uses_levels,
        "status": round_obj.status,
        "size": round_obj.size,
        "answered": answered,
        "correct": round_obj.reviews.filter(is_correct=True).count(),
        "level": progress.level if round_obj.topic.uses_levels else None,
        "question": (
            QuestionSerializer(current, context={"saved_ids": saved_ids}).data
            if current and round_obj.status == "active"
            else None
        ),
    }


def next_question(round_obj, user):
    used = list(round_obj.reviews.values_list("question_id", flat=True))
    progress = get_progress(user, round_obj.topic)
    pk = pick_question(user, round_obj.topic, progress.level, used)
    return Question.objects.prefetch_related("choices").get(pk=pk) if pk else None


def finish(round_obj):
    round_obj.status = "finished"
    round_obj.current_question = None
    round_obj.finished_at = timezone.now()
    round_obj.save()


class RoundCreateView(APIView):
    def post(self, request):
        if get_profile(request.user).role == "mentor":
            raise PermissionDenied("Los mentores no practican temas. Crea cuestionarios y sigue a tus alumnos")
        topic = get_topic(request.user, request.data.get("topic"))
        try:
            size = int(request.data.get("size") or MIN_ROUND)
        except (TypeError, ValueError):
            size = MIN_ROUND
        size = max(MIN_ROUND, min(size, MAX_ROUND))
        if not topic.questions.exists():
            raise ValidationError({"topic": ["Este tema no tiene preguntas"]})
        get_profile(request.user).topics.add(topic)
        progress = get_progress(request.user, topic)
        if topic.uses_levels and not progress.fixed:
            # Primera ronda del tema. El nivel elegido queda fijado y desde aquí solo cambia respondiendo
            level = progress.level
            if "level" in request.data:
                try:
                    level = int(request.data["level"])
                except (TypeError, ValueError):
                    level = 0
                if not 1 <= level <= 5:
                    raise ValidationError({"level": ["El nivel debe ser un número del 1 al 5"]})
            set_level(progress, level)
            progress.max_level = level
            progress.fixed = True
            progress.save(update_fields=["max_level", "fixed"])
        with transaction.atomic():
            Round.objects.filter(user=request.user, topic=topic, status="active").update(status="abandoned")
            round_obj = Round.objects.create(
                user=request.user, topic=topic, size=size, start_level=progress.level
            )
            question = next_question(round_obj, request.user)
            round_obj.current_question = question
            round_obj.save(update_fields=["current_question"])
        return Response(round_data(round_obj, request, question), status=status.HTTP_201_CREATED)


class RoundDetailView(APIView):
    def get(self, request, pk):
        round_obj = get_object_or_404(Round.objects.select_related("topic", "current_question"), pk=pk, user=request.user)
        return Response(round_data(round_obj, request))


class RoundAnswerView(APIView):
    def post(self, request, pk):
        with transaction.atomic():
            round_obj = get_object_or_404(
                Round.objects.select_for_update(of=("self",)).select_related("topic", "current_question"),
                pk=pk, user=request.user,
            )
            if round_obj.status != "active" or round_obj.current_question is None:
                return Response({"detail": "La ronda ya ha terminado"}, status=status.HTTP_409_CONFLICT)
            question = round_obj.current_question
            choice = question.choices.filter(pk=request.data.get("choice")).first()
            if choice is None:
                raise ValidationError({"choice": ["Elige una opción de esta pregunta"]})
            correct_choice = question.choices.get(is_correct=True)

            change = None
            progress = get_progress(request.user, round_obj.topic)
            if round_obj.topic.uses_levels:
                progress = type(progress).objects.select_for_update().get(pk=progress.pk)
                change = apply_answer(progress, choice.is_correct)
                progress.save()
            Review.objects.create(
                user=request.user, question=question, choice=choice, is_correct=choice.is_correct, round=round_obj,
                level=question.level, level_after=progress.level if round_obj.topic.uses_levels else None,
            )
            answered = round_obj.reviews.count()
            following = None if answered >= round_obj.size else next_question(round_obj, request.user)
            if following is None:
                finish(round_obj)
            else:
                round_obj.current_question = following
                round_obj.save(update_fields=["current_question"])
        bump_stats(request.user.id)
        result = {
            "correct": choice.is_correct,
            "correct_choice": correct_choice.id,
            "explanation": question.explanation,
            "level_change": change,
            "round": round_data(round_obj, request, following),
        }
        return Response(result)


class RoundAbandonView(APIView):
    def post(self, request, pk):
        round_obj = get_object_or_404(Round, pk=pk, user=request.user, status="active")
        round_obj.status = "abandoned"
        round_obj.current_question = None
        round_obj.save()
        return Response({"status": "abandoned"})


class ActiveRoundView(APIView):
    """Ronda en curso de un tema, para poder continuarla."""

    def get(self, request, topic_id):
        round_obj = (
            Round.objects.select_related("topic", "current_question")
            .filter(user=request.user, topic_id=topic_id, status="active")
            .first()
        )
        if not round_obj:
            return Response({"detail": "No hay ronda en curso"}, status=status.HTTP_404_NOT_FOUND)
        return Response(round_data(round_obj, request))


class SavedListView(APIView):
    def get(self, request):
        saved = request.user.saved_questions.select_related("question__topic__owner").prefetch_related("question__choices")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(saved, request)
        questions = [item.question for item in page]
        data = QuestionDetailSerializer(questions, many=True, context={"saved_ids": {q.id for q in questions}}).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        question = get_object_or_404(Question, pk=request.data.get("question"))
        if not can_access_question(request.user, question):
            raise PermissionDenied("No tienes acceso a esta pregunta")
        try:
            with transaction.atomic():
                SavedQuestion.objects.create(user=request.user, question=question)
        except IntegrityError:
            pass
        return Response({"saved": True}, status=status.HTTP_201_CREATED)


class SavedDeleteView(APIView):
    def delete(self, request, question_id):
        request.user.saved_questions.filter(question_id=question_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def has_revealed(user, question):
    from offers.models import OfferAnswer

    return (
        Review.objects.filter(user=user, question=question).exists()
        or SavedQuestion.objects.filter(user=user, question=question).exists()
        or OfferAnswer.objects.filter(attempt__user=user, attempt__status="finished", question=question).exists()
    )


class QuestionDetailView(APIView):
    def get(self, request, pk):
        question = get_object_or_404(Question.objects.select_related("topic__owner").prefetch_related("choices"), pk=pk)
        if not can_access_question(request.user, question):
            raise PermissionDenied("No tienes acceso a esta pregunta")
        saved_ids = set(request.user.saved_questions.filter(question=question).values_list("question_id", flat=True))
        revealed = has_revealed(request.user, question) or role_of(request.user) == "mentor"
        serializer = QuestionDetailSerializer if revealed else QuestionSerializer
        return Response(serializer(question, context={"saved_ids": saved_ids}).data)


class AssistantView(APIView):
    """Chatbot de una pregunta. Tiene límite diario de mensajes por usuario."""

    def _question(self, request, pk):
        question = get_object_or_404(Question.objects.select_related("topic__owner").prefetch_related("choices"), pk=pk)
        if not can_access_question(request.user, question):
            raise PermissionDenied("No tienes acceso a esta pregunta")
        return question

    def _usage(self, user):
        """Mensajes enviados hoy y en los últimos 7 días, y los que quedan según los dos límites."""
        mine = AssistantMessage.objects.filter(user=user, role="user")
        today = mine.filter(created_at__date=timezone.localdate()).count()
        week = mine.filter(created_at__gte=timezone.now() - timedelta(days=7)).count()
        day_left = max(0, settings.CHATBOT_DAILY_LIMIT - today)
        week_left = max(0, settings.CHATBOT_WEEKLY_LIMIT - week)
        return {
            "remaining": min(day_left, week_left),
            "remaining_today": day_left,
            "remaining_week": week_left,
            "limit": settings.CHATBOT_DAILY_LIMIT,
            "weekly_limit": settings.CHATBOT_WEEKLY_LIMIT,
        }

    def get(self, request, pk):
        question = self._question(request, pk)
        messages = AssistantMessage.objects.filter(user=request.user, question=question)
        return Response({"messages": AssistantMessageSerializer(messages, many=True).data, **self._usage(request.user)})

    def post(self, request, pk):
        question = self._question(request, pk)
        text = str(request.data.get("text") or "").strip()
        if not text or len(text) > 1000:
            raise ValidationError({"text": ["Escribe una duda de hasta 1000 caracteres"]})
        usage = self._usage(request.user)
        if usage["remaining_today"] == 0:
            return Response(
                {"detail": f"Has llegado al límite de {usage['limit']} mensajes al día con el chatbot. Mañana podrás seguir"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if usage["remaining_week"] == 0:
            return Response(
                {"detail": f"Has llegado al límite de {usage['weekly_limit']} mensajes a la semana con el chatbot"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if not is_configured():
            return Response(
                {"detail": "Falta configurar la clave de IA (GEMINI_API_KEY o ANTHROPIC_API_KEY) en el archivo .env"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        history = list(AssistantMessage.objects.filter(user=request.user, question=question))
        try:
            reply = ai.answer_doubt(question, history, text, has_revealed(request.user, question))
        except AIUnavailable as exc:
            logger.warning("assistant failed user=%s error=%s", request.user.pk, exc)
            return Response({"detail": "El chatbot no está disponible ahora. Inténtalo en un momento"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        AssistantMessage.objects.create(user=request.user, question=question, role="user", text=text)
        answer = AssistantMessage.objects.create(user=request.user, question=question, role="assistant", text=reply)
        return Response({"message": AssistantMessageSerializer(answer).data, **self._usage(request.user)})


class StatsView(APIView):
    def get(self, request):
        topic = request.query_params.get("topic")
        params = {"topic": topic or ""}
        key = stats_key(request.user.id, params)
        data = cache.get(key)
        if data is None:
            data = build_stats(request.user, int(topic) if topic and topic.isdigit() else None)
            cache.set(key, data, STATS_TTL)
        return Response(data)
