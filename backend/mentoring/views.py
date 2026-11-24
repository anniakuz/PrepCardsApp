from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import get_profile, role_of
from accounts.permissions import IsMentor
from quiz.access import accessible_topics, can_access_question
from quiz.models import Question, Review, Topic
from quiz.stats import build_stats

from .models import Enrollment, Message
from .serializers import EnrollmentSerializer, MentorSerializer
from .services import broadcast, create_message, message_payload

User = get_user_model()
MAX_REQUEST = 500


def my_enrollment(user, pk):
    return get_object_or_404(Enrollment.objects.select_related("mentor", "student"), Q(mentor=user) | Q(student=user), pk=pk)


def clean_text(value, limit):
    return str(value or "").strip()[:limit]


class MentorListView(APIView):
    """Mentores que aceptan solicitudes, con la relación que ya tengo con cada uno."""

    def get(self, request):
        mentors = User.objects.filter(
            profile__role="mentor", profile__accepting_requests=True, is_active=True
        ).exclude(pk=request.user.pk).select_related("profile")
        search = request.query_params.get("q", "").strip()
        if search:
            # Un solo buscador. Nombre, usuario, descripción y tecnologías (temas del mentor y los que ha creado)
            mentors = mentors.filter(
                Q(username__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)
                | Q(profile__about__icontains=search) | Q(profile__topics__name__icontains=search)
                | Q(created_topics__name__icontains=search, created_topics__visibility__in=["public", "official"])
            ).distinct()
        relations = {
            e.mentor_id: e.status
            for e in Enrollment.objects.filter(student=request.user, status__in=["pending", "active"])
        }
        mentors = [m for m in mentors.order_by("username")[:100] if m.id not in relations]
        return Response(MentorSerializer(mentors, many=True, context={"relations": relations}).data)


class MentorStatsView(APIView):
    """Resumen para el mentor. Sus cuestionarios y sus alumnos."""

    permission_classes = [IsMentor]

    def get(self, request):
        quizzes = []
        for topic in Topic.objects.filter(owner=request.user).order_by("name"):
            reviews = Review.objects.filter(question__topic=topic).exclude(user=request.user)
            answers = reviews.count()
            correct = reviews.filter(is_correct=True).count()
            quizzes.append({
                "id": topic.id, "name": topic.label, "visibility": topic.visibility, "publish_status": topic.publish_status,
                "question_count": topic.questions.count(),
                "learners": reviews.values("user").distinct().count(),
                "answers": answers, "accuracy": round(100 * correct / answers) if answers else None,
            })
        students = []
        enrollments = Enrollment.objects.filter(mentor=request.user, status="active").select_related("student")
        for e in enrollments:
            item = {"enrollment": e.id, "username": e.student.username, "shares_stats": e.share_stats, "shares_answers": e.share_answers}
            if e.share_stats:
                reviews = Review.objects.filter(user=e.student)
                answers = reviews.count()
                correct = reviews.filter(is_correct=True).count()
                item.update(answers=answers, accuracy=round(100 * correct / answers) if answers else None)
            students.append(item)
        return Response({"quizzes": quizzes, "students": students})


class EnrollmentListView(APIView):
    def get(self, request):
        queryset = Enrollment.objects.filter(Q(mentor=request.user) | Q(student=request.user)).select_related("mentor", "student")
        return Response(EnrollmentSerializer(queryset, many=True, context={"request": request}).data)

    def post(self, request):
        mentor = User.objects.filter(pk=request.data.get("mentor"), is_active=True).select_related("profile").first()
        if mentor is None or role_of(mentor) != "mentor":
            raise ValidationError({"mentor": ["Mentor no encontrado"]})
        if mentor.pk == request.user.pk:
            raise ValidationError({"mentor": ["No puedes ser tu propio mentor"]})
        if not get_profile(mentor).accepting_requests:
            return Response({"detail": "Este mentor no está disponible ahora"}, status=status.HTTP_409_CONFLICT)
        message = clean_text(request.data.get("message"), MAX_REQUEST)
        if not message:
            raise ValidationError({"message": ["Escribe un mensaje para el mentor"]})
        try:
            with transaction.atomic():
                enrollment = Enrollment.objects.create(mentor=mentor, student=request.user, request_message=message)
        except IntegrityError:
            return Response({"detail": "Ya tienes una solicitud abierta con este mentor"}, status=status.HTTP_409_CONFLICT)
        return Response(EnrollmentSerializer(enrollment, context={"request": request}).data, status=status.HTTP_201_CREATED)


class EnrollmentDetailView(APIView):
    """El estudiante edita su mensaje mientras está pendiente y decide qué comparte con el mentor."""

    def patch(self, request, pk):
        enrollment = my_enrollment(request.user, pk)
        if enrollment.student_id != request.user.id:
            raise PermissionDenied("Solo el estudiante puede cambiar esto")
        if "request_message" in request.data:
            if enrollment.status != "pending":
                raise ValidationError({"request_message": ["Solo se puede editar mientras está pendiente"]})
            message = clean_text(request.data["request_message"], MAX_REQUEST)
            if not message:
                raise ValidationError({"request_message": ["El mensaje no puede estar vacío"]})
            enrollment.request_message = message
        if "share_data" in request.data:
            # Una sola casilla. Compartir datos incluye estadísticas y respuestas
            enrollment.share_stats = enrollment.share_answers = bool(request.data["share_data"])
        for field in ("share_stats", "share_answers"):
            if field in request.data:
                setattr(enrollment, field, bool(request.data[field]))
        enrollment.save()
        return Response(EnrollmentSerializer(enrollment, context={"request": request}).data)


class EnrollmentActionView(APIView):
    """accept y reject los hace el mentor sobre una solicitud pendiente. end lo puede hacer cualquiera de los dos."""

    def post(self, request, pk, action):
        enrollment = my_enrollment(request.user, pk)
        if action in ("accept", "reject"):
            if enrollment.mentor_id != request.user.id:
                raise PermissionDenied("Solo el mentor puede responder a la solicitud")
            if enrollment.status != "pending":
                return Response({"detail": "La solicitud ya fue respondida"}, status=status.HTTP_409_CONFLICT)
            enrollment.status = "active" if action == "accept" else "rejected"
        elif action == "end":
            if enrollment.status not in ("pending", "active"):
                return Response({"detail": "La mentoría ya terminó"}, status=status.HTTP_409_CONFLICT)
            enrollment.status = "ended"
        else:
            raise ValidationError({"action": ["Acción no válida"]})
        enrollment.save()
        return Response(EnrollmentSerializer(enrollment, context={"request": request}).data)


def mark_read(enrollment, user):
    field = "mentor_read_at" if enrollment.mentor_id == user.id else "student_read_at"
    setattr(enrollment, field, timezone.now())
    enrollment.save(update_fields=[field])


class NotificationsView(APIView):
    """Avisos del menú. Solicitudes pendientes (mentor) y mensajes sin leer en mentorías activas."""

    def get(self, request):
        user = request.user
        pending = Enrollment.objects.filter(mentor=user, status="pending").count()
        unread = {}
        for enrollment in Enrollment.objects.filter(Q(mentor=user) | Q(student=user), status="active"):
            read_at = enrollment.mentor_read_at if enrollment.mentor_id == user.id else enrollment.student_read_at
            messages = enrollment.messages.exclude(sender=user)
            if read_at:
                messages = messages.filter(created_at__gt=read_at)
            count = messages.count()
            if count:
                unread[enrollment.id] = count
        return Response({
            "pending_requests": pending,
            "unread": unread,
            "unread_messages": sum(unread.values()),
            "total": pending + sum(unread.values()),
        })


class MarkReadView(APIView):
    def post(self, request, pk):
        mark_read(my_enrollment(request.user, pk), request.user)
        return Response({"read": True})


class MessageListView(APIView):
    def get(self, request, pk):
        enrollment = my_enrollment(request.user, pk)
        mark_read(enrollment, request.user)
        messages = enrollment.messages.select_related("sender", "question", "topic")
        return Response([message_payload(m) for m in messages])

    def post(self, request, pk):
        enrollment = my_enrollment(request.user, pk)
        if enrollment.status != "active":
            return Response({"detail": "El chat solo está abierto en mentorías activas"}, status=status.HTTP_409_CONFLICT)
        is_mentor = enrollment.mentor_id == request.user.id
        text = clean_text(request.data.get("text"), 2000)
        question = topic = None

        if request.data.get("question"):
            if is_mentor:
                raise PermissionDenied("Solo el estudiante envía preguntas desde la práctica")
            question = get_object_or_404(Question.objects.select_related("topic", "job_offer"), pk=request.data["question"])
            if question.topic_id is None:
                if question.job_offer_id is None or question.job_offer.user_id != request.user.id:
                    raise PermissionDenied("No tienes acceso a esta pregunta")
            else:
                if not accessible_topics(request.user).filter(pk=question.topic_id).exists():
                    raise PermissionDenied("No tienes acceso a esta pregunta")
                owner = question.topic.owner_id
                if question.topic.visibility == "private" and owner != enrollment.mentor_id:
                    raise PermissionDenied("Esta pregunta es de un tema privado. Solo puedes preguntar al chatbot o a su mentor creador")

        if request.data.get("topic"):
            if not is_mentor:
                raise PermissionDenied("Solo el mentor puede enviar temas")
            topic = get_object_or_404(Topic, pk=request.data["topic"], owner=request.user)
            if not topic.questions.exists():
                raise ValidationError({"topic": ["El tema no tiene preguntas"]})

        if not text and question is None and topic is None:
            raise ValidationError({"text": ["Escribe un mensaje"]})
        message = create_message(enrollment, request.user, text, question, topic)
        broadcast(message)
        return Response(message_payload(message), status=status.HTTP_201_CREATED)


class StudentDataView(APIView):
    """Estadísticas o respuestas de un estudiante, solo si él las comparte con su mentor."""

    kind = "stats"

    def get(self, request, pk):
        enrollment = my_enrollment(request.user, pk)
        if enrollment.mentor_id != request.user.id or enrollment.status != "active":
            raise PermissionDenied("Solo el mentor de una mentoría activa puede verlo")
        if self.kind == "stats":
            if not enrollment.share_stats:
                raise PermissionDenied("El estudiante no comparte sus estadísticas")
            return Response(build_stats(enrollment.student))
        if not enrollment.share_answers:
            raise PermissionDenied("El estudiante no comparte sus respuestas")
        reviews = Review.objects.filter(user=enrollment.student).select_related("question", "choice").order_by("-created_at")[:200]
        return Response([
            {
                "question": r.question.text, "level": r.level, "answer": r.choice.text if r.choice else "",
                "is_correct": r.is_correct, "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ])


class AvailabilityView(APIView):
    permission_classes = [IsMentor]

    def put(self, request):
        profile = get_profile(request.user)
        profile.accepting_requests = bool(request.data.get("accepting_requests"))
        profile.save()
        return Response({"accepting_requests": profile.accepting_requests})
