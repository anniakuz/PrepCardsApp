import io
import json
from unittest import mock

import pytest
from django.core import mail

from config.ai_client import AIUnavailable
from quiz.models import Question, TopicProgress, Topic
from quiz.tasks import send_practice_reminders
from quiz.tests.helpers import api_for, make_user, question_json

pytestmark = pytest.mark.django_db


def topic_id(slug):
    return Topic.objects.get(slug=slug, owner=None).id


def answer(client, round_id, correct, question):
    choices = Question.objects.get(pk=question["id"]).choices.all()
    pick = next(c for c in choices if c.is_correct == correct)
    return client.post(f"/api/rounds/{round_id}/answer/", {"choice": pick.id}, format="json")


def test_catalog_shows_official_topics_with_questions_only(client):
    names = [t["name"] for t in client.get("/api/topics/").data["results"]]
    assert set(names) == {"Java", "Python", "React", "HTML/CSS", "SQL", "Linux", "Patrones de diseño", "AWS Cloud"}


def test_catalog_kind_filters_official_and_community(client, user):
    assert len(client.get("/api/topics/?kind=official").data["results"]) == 8
    assert client.get("/api/topics/?kind=community").data["results"] == []
    other = make_user("otra")
    Topic.objects.create(name="Publico", slug="publico", owner=other, visibility="public", publish_status="approved")
    Topic.objects.create(name="Pendiente", slug="pendiente", owner=other, visibility="public", publish_status="pending")
    Question.objects.bulk_create([Question(topic=t, text="¿?") for t in Topic.objects.filter(slug__in=["publico", "pendiente"])])
    names = [t["name"] for t in client.get("/api/topics/?kind=community").data["results"]]
    assert names == ["Publico"]


def test_catalog_search_and_popular(client, user):
    from accounts.models import get_profile

    get_profile(user).topics.add(Topic.objects.get(slug="react", owner=None))
    assert [t["name"] for t in client.get("/api/topics/?q=pyth").data["results"]] == ["Python"]
    assert client.get("/api/topics/popular/").data[0]["name"] == "React"


def test_round_questions_show_level_and_hide_answer(client):
    data = client.post("/api/rounds/", {"topic": topic_id("java")}, format="json").data
    assert data["level"] == 2 and data["size"] == 20
    question = data["question"]
    assert question["level"] == 2
    assert all(set(c) == {"id", "text"} for c in question["choices"])


def test_five_hits_raise_level_and_questions_follow(client, user):
    data = client.post("/api/rounds/", {"topic": topic_id("java")}, format="json").data
    changes = []
    for _ in range(5):
        result = answer(client, data["id"], True, data["question"]).data
        changes.append(result["level_change"])
        data = result["round"]
    assert changes == [None, None, None, None, "up"]
    assert data["level"] == 3 and data["question"]["level"] == 3
    assert TopicProgress.objects.get(user=user).max_level == 3


def test_three_misses_lower_level(client):
    data = client.post("/api/rounds/", {"topic": topic_id("java"), "level": 3}, format="json").data
    assert data["level"] == 3
    for _ in range(3):
        result = answer(client, data["id"], False, data["question"]).data
        data = result["round"]
    assert result["level_change"] == "down" and data["level"] == 2


def test_answer_reveals_correct_choice_and_explanation(client):
    data = client.post("/api/rounds/", {"topic": topic_id("python")}, format="json").data
    result = answer(client, data["id"], False, data["question"]).data
    assert result["correct"] is False and result["explanation"]
    assert result["correct_choice"] != 0


def test_round_finishes_after_its_size(client):
    data = client.post("/api/rounds/", {"topic": topic_id("java")}, format="json").data
    seen = set()
    while data["status"] == "active":
        seen.add(data["question"]["id"])
        data = answer(client, data["id"], True, data["question"]).data["round"]
    assert data["status"] == "finished" and data["answered"] == len(seen) == 20
    assert client.post(f"/api/rounds/{data['id']}/answer/", {"choice": 1}, format="json").status_code == 409


def test_cannot_answer_with_a_choice_of_another_question(client):
    data = client.post("/api/rounds/", {"topic": topic_id("java")}, format="json").data
    other = Question.objects.exclude(pk=data["question"]["id"]).first().choices.first()
    assert client.post(f"/api/rounds/{data['id']}/answer/", {"choice": other.id}, format="json").status_code == 400


def test_start_level_is_fixed_once_the_topic_starts(client):
    topic = topic_id("react")
    assert client.put(f"/api/topics/{topic}/level/", {"level": 4}, format="json").data["level"] == 4
    assert client.put(f"/api/topics/{topic}/level/", {"level": 9}, format="json").status_code == 400
    data = client.post("/api/rounds/", {"topic": topic}, format="json").data
    assert data["question"]["level"] == 4
    assert client.get(f"/api/topics/{topic}/level/").data["fixed"] is True
    assert client.put(f"/api/topics/{topic}/level/", {"level": 2}, format="json").status_code == 409
    again = client.post("/api/rounds/", {"topic": topic, "level": 1}, format="json").data
    assert again["level"] == 4


def test_stats_show_level_evolution(client):
    data = client.post("/api/rounds/", {"topic": topic_id("java")}, format="json").data
    for _ in range(5):
        data = answer(client, data["id"], True, data["question"]).data["round"]
    stats = client.get("/api/stats/").data
    java = next(t for t in stats["topics"] if t["name"] == "Java")
    assert stats["total"] == 5 and java["level"] == 3 and java["max_level"] == 3
    assert java["evolution"] == [2, 2, 2, 2, 3]


def test_save_and_list_saved_questions(client):
    question = Question.objects.first()
    assert client.post("/api/saved/", {"question": question.id}, format="json").status_code == 201
    assert client.post("/api/saved/", {"question": question.id}, format="json").status_code == 201
    saved = client.get("/api/saved/").data
    assert saved["count"] == 1 and any(c["is_correct"] for c in saved["results"][0]["choices"])
    assert client.delete(f"/api/saved/{question.id}/").status_code == 204
    assert client.get("/api/saved/").data["count"] == 0


def test_question_detail_hides_answer_until_answered(client):
    question = Question.objects.first()
    assert "explanation" not in client.get(f"/api/questions/{question.id}/").data
    client.post("/api/saved/", {"question": question.id}, format="json")
    assert "explanation" in client.get(f"/api/questions/{question.id}/").data


# Temas propios

def upload(client, count=20, levels=True, **extra):
    file = io.BytesIO(json.dumps(question_json(count, levels)).encode())
    file.name = "preguntas.json"
    return client.post("/api/topics/", {"name": "Java/SpringBoot", "file": file, **extra}, format="multipart")


def test_example_file_can_be_downloaded(client):
    response = client.get("/api/topics/example/")
    assert response.status_code == 200 and json.loads(response.content)["questions"]


def test_create_private_topic_from_json(client, user):
    response = upload(client)
    assert response.status_code == 201
    assert response.data["label"] == "Java/SpringBoot creado por annia"
    assert response.data["visibility"] == "private" and response.data["question_count"] == 20
    assert Topic.objects.get(pk=response.data["id"]).questions.filter(level=5).count() == 4


def test_topic_names_do_not_need_to_be_unique(client):
    assert upload(client).status_code == 201 and upload(client).status_code == 201
    assert upload(make_client := api_for(make_user("otra"))).status_code == 201
    assert Topic.objects.filter(name="Java/SpringBoot").count() == 3


def test_json_with_less_than_20_questions_is_rejected(client):
    response = upload(client, count=19)
    assert response.status_code == 400 and "al menos 20" in response.data["questions"][0]


def test_json_errors_say_which_question_fails(client):
    data = question_json(20)
    data["questions"][4]["choices"] = ["a", "a", "b", "c"]
    data["questions"][7]["answer"] = 9
    file = io.BytesIO(json.dumps(data).encode())
    file.name = "x.json"
    response = client.post("/api/topics/", {"name": "T", "file": file}, format="multipart")
    assert response.status_code == 400
    errors = response.data["questions"]
    assert any(e.startswith("Pregunta 5") for e in errors) and any(e.startswith("Pregunta 8") for e in errors)


def test_levels_must_be_on_all_questions_or_none(client):
    data = question_json(20)
    del data["questions"][0]["level"]
    file = io.BytesIO(json.dumps(data).encode())
    file.name = "x.json"
    assert client.post("/api/topics/", {"name": "T", "file": file}, format="multipart").status_code == 400


def test_topic_without_levels_is_practiced_without_adaptation(client):
    topic = upload(client, levels=False).data
    assert topic["uses_levels"] is False
    data = client.post("/api/rounds/", {"topic": topic["id"]}, format="json").data
    assert data["level"] is None and data["question"]["level"] is None
    result = answer(client, data["id"], True, data["question"]).data
    assert result["level_change"] is None


def test_private_topic_is_hidden_from_others(client, user):
    topic = upload(client).data
    other = api_for(make_user("otra"))
    assert other.get(f"/api/topics/{topic['id']}/").status_code == 404
    assert topic["id"] not in [t["id"] for t in other.get("/api/topics/").data["results"]]
    assert other.post("/api/rounds/", {"topic": topic["id"]}, format="json").status_code == 404


@mock.patch("quiz.ai.verify_questions")
def test_public_topic_is_published_only_if_ai_finds_no_errors(verify, client, settings):
    settings.ANTHROPIC_API_KEY = "test"
    verify.side_effect = lambda batch: [{"index": q["index"], "ok": True, "problem": ""} for q in batch]
    topic = upload(client, visibility="public").data
    assert (topic["visibility"], topic["publish_status"]) == ("public", "approved")
    assert topic["id"] in [t["id"] for t in api_for(make_user("otra")).get("/api/topics/").data["results"]]


@mock.patch("quiz.ai.verify_questions")
def test_rejected_topic_stays_private_and_reports_each_error(verify, client, settings):
    settings.ANTHROPIC_API_KEY = "test"
    verify.side_effect = lambda batch: [
        {"index": q["index"], "ok": q["index"] != 3, "problem": "La respuesta correcta es la B" if q["index"] == 3 else ""}
        for q in batch
    ]
    topic = upload(client, visibility="public").data
    assert (topic["visibility"], topic["publish_status"]) == ("private", "rejected")
    assert [(r["position"], r["problem"]) for r in topic["publish_report"]] == [(3, "La respuesta correcta es la B")]


def test_public_topic_without_api_key_is_refused(client, settings):
    settings.ANTHROPIC_API_KEY = ""
    assert upload(client, visibility="public").status_code == 503
    assert not Topic.objects.filter(name="Java/SpringBoot").exists()


@mock.patch("quiz.ai.verify_questions", side_effect=AIUnavailable("sin servicio"))
def test_ai_failure_is_not_a_rejection_and_keeps_topic_private(verify, client, settings):
    settings.ANTHROPIC_API_KEY = "test"
    topic = upload(client, visibility="public").data
    assert topic["publish_status"] == "error" and topic["visibility"] == "private"
    assert topic["publish_report"][0]["problem"] == "sin servicio"


def test_only_owner_manages_topic_and_official_only_admin(client, user):
    topic = upload(client).data
    other = api_for(make_user("otra"))
    assert other.delete(f"/api/topics/{topic['id']}/").status_code == 404
    assert client.delete(f"/api/topics/{topic_id('java')}/").status_code == 403
    admin = api_for(make_user("jefa", role="admin"))
    assert admin.patch(f"/api/topics/{topic_id('java')}/", {"description": "x"}, format="json").status_code == 200
    assert client.delete(f"/api/topics/{topic['id']}/").status_code == 204


def test_replacing_questions_sends_published_topic_back_to_private(client, settings):
    settings.ANTHROPIC_API_KEY = "test"
    with mock.patch("quiz.ai.verify_questions", side_effect=lambda b: [{"index": q["index"], "ok": True, "problem": ""} for q in b]):
        topic = upload(client, visibility="public").data
    file = io.BytesIO(json.dumps(question_json(25)).encode())
    file.name = "n.json"
    updated = client.put(f"/api/topics/{topic['id']}/questions/", {"file": file}, format="multipart").data
    assert updated["visibility"] == "private" and updated["question_count"] == 25


# Chatbot

@mock.patch("quiz.ai.call_text", return_value="Porque la JVM lo exige")
def test_chatbot_answers_and_has_daily_limit(call, client, settings):
    settings.ANTHROPIC_API_KEY = "test"
    settings.CHATBOT_DAILY_LIMIT = 2
    settings.CHATBOT_WEEKLY_LIMIT = 20
    question = Question.objects.first()
    url = f"/api/questions/{question.id}/assistant/"
    first = client.post(url, {"text": "¿Por qué?"}, format="json")
    assert first.status_code == 200 and first.data["remaining"] == 1
    assert client.post(url, {"text": "¿Y entonces?"}, format="json").data["remaining"] == 0
    assert client.post(url, {"text": "¿Una más?"}, format="json").status_code == 429
    history = client.get(url).data
    assert history["remaining"] == 0 and len(history["messages"]) == 4


@mock.patch("quiz.ai.call_text", return_value="ok")
def test_chatbot_does_not_reveal_answer_before_responding(call, client, settings):
    settings.ANTHROPIC_API_KEY = "test"
    question = Question.objects.first()
    client.post(f"/api/questions/{question.id}/assistant/", {"text": "pista"}, format="json")
    system = call.call_args.args[0]
    assert "(correcta)" not in system and "No le digas" in system


def test_chatbot_without_key_and_private_topic_access(client, settings):
    settings.ANTHROPIC_API_KEY = ""
    question = Question.objects.first()
    assert client.post(f"/api/questions/{question.id}/assistant/", {"text": "hola"}, format="json").status_code == 503
    topic = upload(client).data
    private_question = Question.objects.filter(topic_id=topic["id"]).first()
    other = api_for(make_user("otra"))
    assert other.post(f"/api/questions/{private_question.id}/assistant/", {"text": "hola"}, format="json").status_code == 403


def test_practice_reminder_only_for_users_who_practiced_this_week_but_not_today(client, user):
    data = client.post("/api/rounds/", {"topic": topic_id("java")}, format="json").data
    answer(client, data["id"], True, data["question"])
    assert send_practice_reminders() == 0
    from django.utils import timezone
    from datetime import timedelta
    from quiz.models import Review

    Review.objects.update(created_at=timezone.now() - timedelta(days=2))
    assert send_practice_reminders() == 1 and len(mail.outbox) == 1


@mock.patch("quiz.ai.call_text", return_value="ok")
def test_chatbot_has_a_weekly_limit_too(call, client, user, settings):
    from datetime import timedelta
    from django.utils import timezone
    from quiz.models import AssistantMessage

    settings.ANTHROPIC_API_KEY = "test"
    settings.CHATBOT_DAILY_LIMIT = 5
    settings.CHATBOT_WEEKLY_LIMIT = 3
    question = Question.objects.first()
    for _ in range(3):
        AssistantMessage.objects.create(user=user, question=question, role="user", text="x")
    AssistantMessage.objects.update(created_at=timezone.now() - timedelta(days=2))
    url = f"/api/questions/{question.id}/assistant/"
    state = client.get(url).data
    assert state["remaining_today"] == 5 and state["remaining_week"] == 0 and state["remaining"] == 0
    response = client.post(url, {"text": "hola"}, format="json")
    assert response.status_code == 429 and "semana" in response.data["detail"]
    AssistantMessage.objects.update(created_at=timezone.now() - timedelta(days=8))
    assert client.post(url, {"text": "hola"}, format="json").status_code == 200
