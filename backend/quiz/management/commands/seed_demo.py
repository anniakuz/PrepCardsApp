import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import get_profile
from quiz.models import Topic

# username, email, rol, nombre, apellidos, experiencia, descripción
USERS = [
    ("admin", "admin@prepcards.local", "admin", "Admin", "PrepCards", "5plus", ""),
    ("estudiante", "estudiante@prepcards.local", "student", "Estela", "Demo", "none", "Quiero prepararme para mi primera entrevista técnica."),
    (
        "mentor", "mentor@prepcards.local", "mentor", "Marta", "Ruiz", "5plus",
        "Backend con 8 años en Java y Spring Boot. Preparo entrevistas técnicas.",
    ),
    (
        "laura_java", "laura@prepcards.local", "mentor", "Laura", "Martín", "5plus",
        "Arquitecta de software. Java, microservicios, SQL y patrones de diseño.",
    ),
    (
        "david_react", "david@prepcards.local", "mentor", "David", "Soler", "4y",
        "Frontend con React y TypeScript. Hooks, rendimiento y accesibilidad.",
    ),
    (
        "sofia_cloud", "sofia@prepcards.local", "mentor", "Sofía", "Vidal", "3y",
        "Ingeniera cloud con AWS y Linux. Te preparo para Solutions Architect.",
    ),
    (
        "carlos_python", "carlos@prepcards.local", "mentor", "Carlos", "Ibáñez", "5plus",
        "Python y Django, APIs, Celery y Docker. Dudas siempre con código.",
    ),
    (
        "nuria_junior", "nuria@prepcards.local", "mentor", "Núria", "Pons", "2y",
        "Fullstack con 2 años de experiencia. Cambié de sector, te entiendo.",
    ),
]


class Command(BaseCommand):
    help = "Crea usuarios de demostración (admin, estudiante y varios mentores con descripción). Solo para desarrollo."

    def handle(self, *args, **options):
        User = get_user_model()
        password = os.environ.get("DEMO_PASSWORD", "demo-prepcards-2026")
        skills = {"mentor": ["java"], "laura_java": ["java", "sql", "patrones-de-diseno"], "david_react": ["react", "html-css"],
                  "sofia_cloud": ["aws-cloud", "linux"], "carlos_python": ["python", "sql"], "nuria_junior": ["react", "python", "html-css"]}
        topics = list(Topic.objects.filter(slug__in=["java", "python", "react"]))
        for username, email, role, first, last, experience, about in USERS:
            user = User.objects.filter(username=username).first()
            created = user is None
            if created:
                if role == "admin":
                    user = User.objects.create_superuser(username, email, password)
                else:
                    user = User.objects.create_user(username, email, password)
                user.first_name, user.last_name = first, last
                user.save()
            profile = get_profile(user)
            profile.role = role
            profile.experience = profile.experience or experience
            profile.age = profile.age or 30
            if not profile.about or len(profile.about) > 75:
                profile.about = about
            profile.save()
            if role == "mentor":
                # Las tecnologías del mentor sirven para que los estudiantes lo encuentren en el buscador
                profile.topics.set(Topic.objects.filter(slug__in=skills.get(username, [])))
            elif created:
                profile.topics.set(topics)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Usuario de demostración creado: {username}"))
