from django.conf import settings
from django.contrib.auth.models import Group
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

ROLES = ["student", "mentor", "admin"]
TERMS_VERSION = "2026-11"


class Profile(models.Model):
    ROLE_CHOICES = [("student", "Estudiante"), ("mentor", "Mentor"), ("admin", "Administrador")]
    SEX_CHOICES = [
        ("female", "Mujer"),
        ("male", "Hombre"),
        ("other", "Otro"),
        ("undisclosed", "Prefiero no decirlo"),
    ]
    EXPERIENCE_CHOICES = [
        ("none", "Sin experiencia"),
        ("6m", "6 meses"),
        ("1y", "1 año"),
        ("2y", "2 años"),
        ("3y", "3 años"),
        ("4y", "4 años"),
        ("5plus", "5 años o más"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="student")
    age = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(14), MaxValueValidator(100)]
    )
    sex = models.CharField(max_length=12, choices=SEX_CHOICES, default="undisclosed")
    experience = models.CharField(max_length=6, choices=EXPERIENCE_CHOICES, default="none")
    about = models.TextField(blank=True, max_length=1000)
    accepting_requests = models.BooleanField(
        default=True, help_text="Solo para mentores. Si está desactivado no reciben solicitudes nuevas"
    )
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    terms_version = models.CharField(max_length=10, blank=True)
    topics = models.ManyToManyField("quiz.Topic", blank=True, related_name="profiles")

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        group, _ = Group.objects.get_or_create(name=self.role)
        self.user.groups.remove(*Group.objects.filter(name__in=ROLES).exclude(pk=group.pk))
        self.user.groups.add(group)


def get_profile(user):
    profile, _ = Profile.objects.get_or_create(
        user=user, defaults={"role": "admin" if user.is_superuser else "student"}
    )
    return profile


def role_of(user):
    if user.is_superuser:
        return "admin"
    return get_profile(user).role
