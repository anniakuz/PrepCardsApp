from django.conf import settings
from django.db import models
from django.db.models import Q


class Enrollment(models.Model):
    """Relación entre un estudiante y un mentor. Nace como solicitud y el chat solo se abre al aceptarla."""

    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("active", "Activa"),
        ("rejected", "Rechazada"),
        ("ended", "Terminada"),
    ]

    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentees")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentors")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    request_message = models.TextField(max_length=500)
    share_stats = models.BooleanField(default=False)
    share_answers = models.BooleanField(default=False)
    mentor_read_at = models.DateTimeField(null=True, blank=True)
    student_read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["mentor", "student"],
                condition=Q(status__in=["pending", "active"]),
                name="unique_open_enrollment",
            ),
            models.CheckConstraint(condition=~Q(mentor=models.F("student")), name="enrollment_not_self"),
        ]


class Message(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    text = models.TextField(blank=True, max_length=2000)
    question = models.ForeignKey("quiz.Question", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    topic = models.ForeignKey(
        "quiz.Topic", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        help_text="Tema privado que el mentor envía al estudiante",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["enrollment", "created_at"], name="message_enr_created_idx")]
