from django.conf import settings
from django.db import models


class JobOffer(models.Model):
    STATUS_CHOICES = [
        ("pending", "Analizando"), ("ready", "Lista"), ("failed", "Error"), ("invalid", "Texto no válido"),
    ]
    GENERATION_CHOICES = [("", "Sin generar"), ("running", "Generando"), ("done", "Terminada"), ("failed", "Error")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offers")
    title = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    raw_text = models.TextField()
    summary = models.TextField(blank=True)
    requirements = models.JSONField(default=list)
    level = models.PositiveSmallIntegerField(default=0, help_text="Nivel que pide la oferta del 1 al 5, 0 si no se sabe")
    level_reason = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ready")
    error = models.TextField(blank=True)
    generation_status = models.CharField(max_length=10, choices=GENERATION_CHOICES, blank=True, default="")
    generation_error = models.TextField(blank=True)
    last_generated = models.PositiveIntegerField(default=0)
    selected_requirements = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Oferta {self.pk}"


class OfferAttempt(models.Model):
    """Una vez que el usuario contesta el cuestionario de una oferta."""

    STATUS_CHOICES = [("active", "En curso"), ("finished", "Terminado")]

    offer = models.ForeignKey(JobOffer, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offer_attempts")
    order = models.JSONField(default=list, help_text="Ids de las preguntas en el orden en que se muestran")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class OfferAnswer(models.Model):
    attempt = models.ForeignKey(OfferAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("quiz.Question", on_delete=models.CASCADE, related_name="+")
    choice = models.ForeignKey("quiz.Choice", on_delete=models.CASCADE, related_name="+")
    correct = models.BooleanField()
    requirement = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "question"], name="unique_answer_per_attempt")]
