from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import get_profile

PASSWORD = "Clave-Segura-2026"


def make_user(username, role="student", **extra):
    user = get_user_model().objects.create_user(username, f"{username}@example.com", PASSWORD)
    profile = get_profile(user)
    profile.role = role
    profile.save()
    return user


def api_for(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


def question_json(count=20, levels=True):
    items = []
    for i in range(count):
        item = {
            "text": f"Pregunta de prueba {i + 1}",
            "choices": [f"a{i}", f"b{i}", f"c{i}", f"d{i}"],
            "answer": i % 4,
            "explanation": "Porque sí",
        }
        if levels:
            item["level"] = i % 5 + 1
        items.append(item)
    return {"questions": items}
