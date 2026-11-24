import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from quiz.importer import parse_questions
from quiz.models import Choice, Question, Topic

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "seed" / "topics"

OFFICIAL_TOPICS = [
    ("java", "Java", "Lenguaje, colecciones, concurrencia y la JVM"),
    ("python", "Python", "Lenguaje, estructuras de datos, generadores y concurrencia"),
    ("react", "React", "Componentes, hooks, estado y rendimiento"),
    ("html-css", "HTML/CSS", "Maquetación, selectores, flexbox, grid y accesibilidad"),
    ("javascript", "JavaScript", "Lenguaje, asincronía, prototipos y el navegador"),
    ("sql", "SQL", "Consultas, joins, índices y transacciones"),
    ("aws-cloud", "AWS Cloud", "Servicios de AWS, redes, almacenamiento y arquitectura"),
    ("algoritmos", "Algoritmos", "Estructuras de datos, complejidad y técnicas clásicas"),
    ("patrones-de-diseno", "Patrones de diseño", "Patrones creacionales, estructurales y de comportamiento"),
    ("linux", "Linux", "Terminal, permisos, procesos y administración básica"),
]


class Command(BaseCommand):
    help = "Crea los temas oficiales y carga las preguntas de quiz/seed/topics/<slug>.json sin duplicar"

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        for slug, name, description in OFFICIAL_TOPICS:
            topic, _ = Topic.objects.get_or_create(
                slug=slug, owner=None, defaults={"name": name, "description": description, "uses_levels": True}
            )
            path = SEED_DIR / f"{slug}.json"
            if not path.exists():
                continue
            parsed, _ = parse_questions(json.loads(path.read_text(encoding="utf-8")), minimum=1)
            existing = set(topic.questions.values_list("text", flat=True))
            for item in parsed:
                if item["text"] in existing:
                    continue
                question = Question.objects.create(
                    topic=topic, level=item["level"], text=item["text"],
                    explanation=item["explanation"], language="es",
                )
                Choice.objects.bulk_create(
                    Choice(question=question, text=text, is_correct=(i == item["answer"]))
                    for i, text in enumerate(item["choices"])
                )
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Temas oficiales listos. Preguntas nuevas: {created}"))
