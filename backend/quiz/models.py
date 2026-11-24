from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

LEVEL_VALIDATORS = [MinValueValidator(1), MaxValueValidator(5)]


class Topic(models.Model):
    """Tema de práctica. Los oficiales no tienen dueño. Los demás los crea un usuario."""

    VISIBILITY_CHOICES = [("official", "Oficial"), ("public", "Público"), ("private", "Privado")]
    PUBLISH_CHOICES = [
        ("", "Sin solicitar"),
        ("pending", "Verificando"),
        ("approved", "Publicado"),
        ("rejected", "Rechazado"),
        ("error", "No se pudo verificar"),
    ]

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=60, blank=True)
    description = models.TextField(blank=True, max_length=500)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="created_topics",
        help_text="Vacío para los temas oficiales",
    )
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default="private")
    uses_levels = models.BooleanField(
        default=True, help_text="Si las preguntas tienen nivel del 1 al 5 y la práctica se adapta"
    )
    shared_with = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="shared_topics")
    publish_status = models.CharField(max_length=10, choices=PUBLISH_CHOICES, blank=True, default="")
    publish_report = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug"], condition=Q(owner__isnull=True), name="unique_official_topic_slug"
            ),
        ]
        indexes = [models.Index(fields=["visibility"], name="topic_visibility_idx")]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:60] or "tema"
        if self.owner_id is None:
            self.visibility = "official"
        elif self.visibility == "official":
            self.visibility = "private"
        super().save(*args, **kwargs)

    @property
    def label(self):
        if self.owner_id is None:
            return self.name
        return f"{self.name} creado por {self.owner.username}"

    def __str__(self):
        return self.label


class Question(models.Model):
    LANGUAGE_CHOICES = [("en", "English"), ("es", "Español")]

    topic = models.ForeignKey(
        Topic, null=True, blank=True, on_delete=models.CASCADE, related_name="questions",
        help_text="Vacío en las preguntas de un cuestionario de oferta, que no pertenecen a ningún tema",
    )
    requirement = models.CharField(max_length=80, blank=True, help_text="Requisito de la oferta al que responde")
    level = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=LEVEL_VALIDATORS,
        help_text="1 inicial, 5 experto. Vacío si el tema no usa niveles",
    )
    text = models.TextField()
    explanation = models.TextField(blank=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="en")
    job_offer = models.ForeignKey(
        "offers.JobOffer", null=True, blank=True, on_delete=models.CASCADE, related_name="questions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["topic", "level"], name="question_topic_level_idx")]

    def __str__(self):
        return self.text[:80]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.TextField()
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.text[:60]


class TopicProgress(models.Model):
    """Nivel actual de un usuario en un tema y sus rachas de aciertos o fallos seguidos."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="topic_progress")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="progress")
    level = models.PositiveSmallIntegerField(default=2, validators=LEVEL_VALIDATORS)
    max_level = models.PositiveSmallIntegerField(default=2, validators=LEVEL_VALIDATORS)
    fixed = models.BooleanField(default=False, help_text="El nivel de partida ya está fijado. Desde entonces solo cambia al responder")
    correct_streak = models.PositiveSmallIntegerField(default=0)
    wrong_streak = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "topic"], name="unique_user_topic_progress")]


class Round(models.Model):
    STATUS_CHOICES = [("active", "En curso"), ("finished", "Terminada"), ("abandoned", "Abandonada")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rounds")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="rounds")
    size = models.PositiveSmallIntegerField(default=20)
    start_level = models.PositiveSmallIntegerField(default=2, validators=LEVEL_VALIDATORS)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    current_question = models.ForeignKey(Question, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "topic", "status"], name="round_user_topic_status_idx")]


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="reviews")
    choice = models.ForeignKey(Choice, null=True, on_delete=models.SET_NULL)
    is_correct = models.BooleanField()
    round = models.ForeignKey(Round, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviews")
    level = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Nivel de la pregunta")
    level_after = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Nivel del usuario tras responder")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "created_at"], name="review_user_created_idx")]


class SavedQuestion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["user", "question"], name="unique_saved_question")]


class AssistantMessage(models.Model):
    """Conversación de un usuario con el chatbot sobre una pregunta."""

    ROLE_CHOICES = [("user", "Usuario"), ("assistant", "Chatbot")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assistant_messages")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="assistant_messages")
    role = models.CharField(max_length=9, choices=ROLE_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["user", "question", "created_at"], name="assistant_user_q_idx")]


class QuestionAudit(models.Model):
    """Historial de cambios de las preguntas de temas oficiales. Lo rellena un trigger de PostgreSQL."""

    question_id = models.BigIntegerField()
    action = models.CharField(max_length=10)
    old_text = models.TextField()
    changed_at = models.DateTimeField()

    class Meta:
        ordering = ["-changed_at"]
