import io
import json

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from config.asgi import application
from mentoring.models import Enrollment
from quiz.models import Question, Topic
from quiz.tests.helpers import api_for, make_user, question_json

pytestmark = pytest.mark.django_db


@pytest.fixture
def active(user, mentor):
    return Enrollment.objects.create(mentor=mentor, student=user, status="active", request_message="hola")


def private_topic(owner):
    file = io.BytesIO(json.dumps(question_json(20)).encode())
    file.name = "p.json"
    return api_for(owner).post("/api/topics/", {"name": "Spring", "file": file}, format="multipart").data


def test_only_available_mentors_are_listed(client, mentor):
    assert [m["username"] for m in client.get("/api/mentors/").data] == ["profe"]
    api_for(mentor).put("/api/mentors/availability/", {"accepting_requests": False}, format="json")
    assert client.get("/api/mentors/").data == []


def test_students_cannot_change_availability(client):
    assert client.put("/api/mentors/availability/", {"accepting_requests": False}, format="json").status_code == 403


def test_request_needs_message_and_available_mentor(client, mentor):
    assert client.post("/api/enrollments/", {"mentor": mentor.id, "message": " "}, format="json").status_code == 400
    api_for(mentor).put("/api/mentors/availability/", {"accepting_requests": False}, format="json")
    response = client.post("/api/enrollments/", {"mentor": mentor.id, "message": "Hola, quiero que seas mi mentor"}, format="json")
    assert response.status_code == 409


def test_request_edit_accept_and_chat_opens_only_after(client, mentor, user):
    created = client.post("/api/enrollments/", {"mentor": mentor.id, "message": "Hola"}, format="json")
    assert created.status_code == 201 and created.data["status"] == "pending"
    pk = created.data["id"]
    assert client.post("/api/enrollments/", {"mentor": mentor.id, "message": "otra"}, format="json").status_code == 409
    assert client.patch(f"/api/enrollments/{pk}/", {"request_message": "Hola, quiero que seas mi mentor"}, format="json").data["request_message"].startswith("Hola, quiero")
    assert client.post(f"/api/enrollments/{pk}/messages/", {"text": "¿estás?"}, format="json").status_code == 409

    boss = api_for(mentor)
    assert client.post(f"/api/enrollments/{pk}/accept/").status_code == 403
    assert boss.post(f"/api/enrollments/{pk}/accept/").data["status"] == "active"
    assert client.patch(f"/api/enrollments/{pk}/", {"request_message": "tarde"}, format="json").status_code == 400
    assert client.post(f"/api/enrollments/{pk}/messages/", {"text": "¿estás?"}, format="json").status_code == 201
    assert [m["text"] for m in boss.get(f"/api/enrollments/{pk}/messages/").data] == ["¿estás?"]


def test_rejected_request_allows_a_new_one(client, mentor):
    pk = client.post("/api/enrollments/", {"mentor": mentor.id, "message": "Hola"}, format="json").data["id"]
    api_for(mentor).post(f"/api/enrollments/{pk}/reject/")
    assert client.post("/api/enrollments/", {"mentor": mentor.id, "message": "Otra vez"}, format="json").status_code == 201


def test_strangers_cannot_read_a_chat(active):
    stranger = api_for(make_user("curiosa"))
    assert stranger.get(f"/api/enrollments/{active.id}/messages/").status_code == 404


def test_student_can_send_an_official_question_to_any_mentor(client, active):
    question = Question.objects.filter(topic__owner=None).first()
    response = client.post(f"/api/enrollments/{active.id}/messages/", {"question": question.id, "text": "No lo entiendo"}, format="json")
    assert response.status_code == 201 and response.data["question"]["id"] == question.id
    assert api_for(active.mentor).get(f"/api/questions/{question.id}/").status_code == 200


def test_private_topic_questions_only_go_to_their_creator(client, user, mentor, active):
    topic = private_topic(user)
    question = Question.objects.filter(topic_id=topic["id"]).first()
    response = client.post(f"/api/enrollments/{active.id}/messages/", {"question": question.id}, format="json")
    assert response.status_code == 403
    other_mentor = make_user("otro", role="mentor")
    ok = Enrollment.objects.create(mentor=other_mentor, student=user, status="active", request_message="hola")
    # el creador del tema es el propio estudiante, así que tampoco lo puede enviar a otro mentor
    assert client.post(f"/api/enrollments/{ok.id}/messages/", {"question": question.id}, format="json").status_code == 403


def test_mentor_topic_sent_by_chat_is_assigned_and_stays_private(client, user, mentor, active):
    topic = private_topic(mentor)
    assert client.get(f"/api/topics/{topic['id']}/").status_code == 404
    boss = api_for(mentor)
    response = boss.post(f"/api/enrollments/{active.id}/messages/", {"topic": topic["id"], "text": "Prepara esto"}, format="json")
    assert response.status_code == 201 and response.data["topic"]["id"] == topic["id"]
    assert client.get(f"/api/topics/{topic['id']}/").status_code == 200
    assert topic["id"] in [t["id"] for t in client.get("/api/topics/mine/").data]
    assert topic["id"] not in [t["id"] for t in api_for(make_user("otra")).get("/api/topics/").data["results"]]

    question = Question.objects.filter(topic_id=topic["id"]).first()
    assert client.post("/api/rounds/", {"topic": topic["id"]}, format="json").status_code == 201
    sent = client.post(f"/api/enrollments/{active.id}/messages/", {"question": question.id}, format="json")
    assert sent.status_code == 201
    other_mentor = make_user("otro", role="mentor")
    second = Enrollment.objects.create(mentor=other_mentor, student=user, status="active", request_message="hola")
    assert client.post(f"/api/enrollments/{second.id}/messages/", {"question": question.id}, format="json").status_code == 403


def test_students_cannot_send_topics(client, user, active):
    topic = private_topic(user)
    assert client.post(f"/api/enrollments/{active.id}/messages/", {"topic": topic["id"]}, format="json").status_code == 403


def test_mentor_sees_stats_and_answers_only_if_student_shares(client, active):
    boss = api_for(active.mentor)
    assert boss.get(f"/api/enrollments/{active.id}/stats/").status_code == 403
    assert boss.get(f"/api/enrollments/{active.id}/reviews/").status_code == 403
    client.patch(f"/api/enrollments/{active.id}/", {"share_stats": True}, format="json")
    assert boss.get(f"/api/enrollments/{active.id}/stats/").status_code == 200
    assert boss.get(f"/api/enrollments/{active.id}/reviews/").status_code == 403
    assert client.get(f"/api/enrollments/{active.id}/stats/").status_code == 403


def token(user):
    return str(AccessToken.for_user(user))


async def connect(enrollment_id, user, **kwargs):
    communicator = WebsocketCommunicator(application, f"/ws/chat/{enrollment_id}/?token={token(user)}", **kwargs)
    communicator.scope["headers"] = [(b"origin", b"http://localhost:5173"), (b"host", b"localhost")]
    connected, code = await communicator.connect()
    return communicator, connected, code


@pytest.mark.django_db(transaction=True)
async def test_websocket_chat_between_student_and_mentor(settings, seeded):
    settings.ALLOWED_HOSTS = ["*"]
    student = await database_sync_to_async(make_user)("alumna")
    boss = await database_sync_to_async(make_user)("jefe", role="mentor")
    enrollment = await database_sync_to_async(Enrollment.objects.create)(
        mentor=boss, student=student, status="active", request_message="hola"
    )
    a, ok_a, _ = await connect(enrollment.id, student)
    b, ok_b, _ = await connect(enrollment.id, boss)
    assert ok_a and ok_b
    await a.send_json_to({"text": "Hola mentor"})
    for side in (a, b):
        received = await side.receive_json_from()
        assert received["text"] == "Hola mentor" and received["sender_name"] == "alumna"
    await a.disconnect()
    await b.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_websocket_rejects_outsiders_and_pending_chats(settings, seeded):
    settings.ALLOWED_HOSTS = ["*"]
    student = await database_sync_to_async(make_user)("alumna")
    boss = await database_sync_to_async(make_user)("jefe", role="mentor")
    stranger = await database_sync_to_async(make_user)("intrusa")
    enrollment = await database_sync_to_async(Enrollment.objects.create)(
        mentor=boss, student=student, status="pending", request_message="hola"
    )
    _, ok, code = await connect(enrollment.id, student)
    assert not ok and code == 4403
    await database_sync_to_async(Enrollment.objects.filter(pk=enrollment.pk).update)(status="active")
    _, ok, code = await connect(enrollment.id, stranger)
    assert not ok and code == 4403


def test_notifications_for_pending_requests_and_unread_messages(client, user, mentor):
    boss = api_for(mentor)
    assert boss.get("/api/mentoring/notifications/").data["total"] == 0
    pk = client.post("/api/enrollments/", {"mentor": mentor.id, "message": "Hola"}, format="json").data["id"]
    assert boss.get("/api/mentoring/notifications/").data["pending_requests"] == 1
    boss.post(f"/api/enrollments/{pk}/accept/")
    assert boss.get("/api/mentoring/notifications/").data["total"] == 0
    boss.post(f"/api/enrollments/{pk}/messages/", {"text": "Bienvenida"}, format="json")
    boss.post(f"/api/enrollments/{pk}/messages/", {"text": "¿Dudas?"}, format="json")
    seen = client.get("/api/mentoring/notifications/").data
    assert seen["unread_messages"] == 2 and seen["unread"] == {str(pk): 2} or seen["unread"] == {pk: 2}
    assert boss.get("/api/mentoring/notifications/").data["total"] == 0
    client.get(f"/api/enrollments/{pk}/messages/")
    assert client.get("/api/mentoring/notifications/").data["total"] == 0
    boss.post(f"/api/enrollments/{pk}/messages/", {"text": "Otro"}, format="json")
    assert client.get("/api/mentoring/notifications/").data["total"] == 1
    assert client.post(f"/api/enrollments/{pk}/read/").status_code == 200
    assert client.get("/api/mentoring/notifications/").data["total"] == 0


def test_one_search_box_finds_mentors_by_name_and_technology(client, mentor):
    from accounts.models import get_profile

    mentor.first_name = "Marta"
    mentor.save()
    get_profile(mentor).topics.add(Topic.objects.get(slug="java"))
    for term in ("profe", "marta", "java"):
        assert [m["username"] for m in client.get(f"/api/mentors/?q={term}").data] == ["profe"]
    assert client.get("/api/mentors/?q=cobol").data == []
    assert client.get("/api/mentors/").data[0]["technologies"] == ["Java"]


def test_mentors_do_not_practice_topics_or_take_offer_quizzes(mentor):
    api = api_for(mentor)
    topic = Topic.objects.get(slug="java")
    assert api.post("/api/rounds/", {"topic": topic.id}, format="json").status_code == 403
    assert api.post("/api/offers/", {"raw_text": "Java"}, format="json").status_code == 403


def test_mentor_stats_cover_own_quizzes_and_students(client, mentor, active):
    from quiz.models import Review

    created = private_topic(mentor)
    question = Question.objects.filter(topic_id=created["id"]).first()
    Review.objects.create(user=active.student, question=question, choice=question.choices.first(), is_correct=True)
    data = api_for(mentor).get("/api/mentors/stats/").data
    quiz = next(q for q in data["quizzes"] if q["id"] == created["id"])
    assert quiz["learners"] == 1 and quiz["answers"] == 1 and quiz["accuracy"] == 100
    assert data["students"][0]["username"] == "annia" and data["students"][0]["shares_stats"] is False
    assert client.get("/api/mentors/stats/").status_code == 403


def test_one_checkbox_shares_stats_and_answers(client, active):
    data = client.patch(f"/api/enrollments/{active.id}/", {"share_data": True}, format="json").data
    assert data["share_data"] is True and data["share_stats"] and data["share_answers"]
    mentor_api = api_for(active.mentor)
    assert mentor_api.get(f"/api/enrollments/{active.id}/stats/").status_code == 200
    assert mentor_api.get(f"/api/enrollments/{active.id}/reviews/").status_code == 200
    client.patch(f"/api/enrollments/{active.id}/", {"share_data": False}, format="json")
    assert mentor_api.get(f"/api/enrollments/{active.id}/stats/").status_code == 403
