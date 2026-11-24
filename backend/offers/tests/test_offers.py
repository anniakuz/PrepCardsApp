from unittest import mock

import pytest

from config.ai_client import AITemporaryError
from offers.models import JobOffer
from quiz.models import Question, Topic

pytestmark = pytest.mark.django_db

TEXT = "Buscamos programador Java con Spring Boot, AWS y Kafka. Dos años de experiencia."
ANALYSIS = {
    "valid": True, "problem": "",
    "title": "Backend Java", "company": "Acme", "summary": "Puesto backend",
    "level": 4, "level_reason": "2 años de experiencia",
    "requirements": [
        {"name": "Java", "category": "language", "importance": "required", "official": "java"},
        {"name": "java", "category": "language", "importance": "required", "official": ""},
        {"name": "AWS", "category": "cloud", "importance": "required", "official": "aws-cloud"},
        {"name": "Spring Boot", "category": "framework", "importance": "required", "official": ""},
        {"name": "Kafka", "category": "architecture", "importance": "nice_to_have", "official": ""},
    ],
}


def questions(requirement, count=4):
    return [
        {"requirement": requirement, "level": 4, "text": f"{requirement} pregunta {i}",
         "choices": ["a", "b", "c", "d"], "correct_index": i % 4, "explanation": "x"}
        for i in range(count)
    ]


def analyze(client, settings, analysis=ANALYSIS):
    settings.ANTHROPIC_API_KEY = "test"
    with mock.patch("offers.ai.call_tool", return_value=analysis):
        return client.post("/api/offers/", {"raw_text": TEXT}, format="json").data["id"]


def build(client, offer_id, selected, generated=()):
    with mock.patch("offers.ai.call_tool", return_value={"questions": list(generated)}) as call:
        response = client.post(f"/api/offers/{offer_id}/generate/", {"requirements": selected}, format="json")
    return response, call


def test_offer_needs_api_key(client, settings):
    settings.ANTHROPIC_API_KEY = ""
    assert client.post("/api/offers/", {"raw_text": TEXT}, format="json").status_code == 503


def test_offer_is_analyzed_and_duplicates_removed(client, settings):
    offer = client.get(f"/api/offers/{analyze(client, settings)}/").data
    assert offer["status"] == "ready" and [r["name"] for r in offer["requirements"]] == ["Java", "AWS", "Spring Boot", "Kafka"]
    assert offer["level"] == 4 and offer["level_reason"] == "2 años de experiencia"
    assert {t["slug"] for t in offer["suggested_topics"]} == {"java", "aws-cloud"}


def test_offer_text_has_no_minimum_length_but_cannot_be_empty(client, settings):
    settings.ANTHROPIC_API_KEY = "test"
    with mock.patch("offers.ai.call_tool", return_value=ANALYSIS):
        assert client.post("/api/offers/", {"raw_text": "Java"}, format="json").status_code == 202
    assert client.post("/api/offers/", {"raw_text": "  "}, format="json").status_code == 400


def test_absurd_text_is_marked_invalid(client, settings):
    bad = {**ANALYSIS, "valid": False, "problem": "Solo dice programador, sin ninguna tecnología.", "requirements": []}
    offer = client.get(f"/api/offers/{analyze(client, settings, bad)}/").data
    assert offer["status"] == "invalid" and "tecnología" in offer["error"]


def test_offer_without_requirements_is_invalid_even_if_ai_says_valid(client, settings):
    empty = {**ANALYSIS, "requirements": []}
    assert client.get(f"/api/offers/{analyze(client, settings, empty)}/").data["status"] == "invalid"


def test_quiz_mixes_official_and_generated_questions_without_creating_a_topic(client, user, settings):
    offer_id = analyze(client, settings)
    response, call = build(client, offer_id, ["Java", "Spring Boot", "AWS"], questions("Spring Boot", 10))
    assert response.status_code == 202
    offer = client.get(f"/api/offers/{offer_id}/").data
    assert offer["generation_status"] == "done" and offer["question_count"] >= 20
    assert offer["selected_requirements"] == ["Java", "Spring Boot", "AWS"]
    assert not Topic.objects.filter(owner=user).exists()
    stored = Question.objects.filter(job_offer_id=offer_id)
    assert all(q.topic_id is None and q.requirement for q in stored)
    assert set(stored.values_list("requirement", flat=True)) == {"Java", "Spring Boot", "AWS"}
    asked = call.call_args[0][1].split("<oferta>")[0]
    assert "Spring Boot" in asked and "nivel 4" in asked and "Kafka" not in asked and "Java:" not in asked


def test_default_level_is_3_when_the_offer_gives_none(client, settings):
    offer_id = analyze(client, settings, {**ANALYSIS, "level": 0, "level_reason": ""})
    _, call = build(client, offer_id, ["Spring Boot"], questions("Spring Boot", 20))
    assert "nivel 3" in call.call_args[0][1]


def test_fully_official_selection_needs_no_ai(client, settings):
    offer_id = analyze(client, settings)
    settings.ANTHROPIC_API_KEY = ""
    response, call = build(client, offer_id, ["Java", "AWS"])
    assert response.status_code == 202 and not call.called
    assert client.get(f"/api/offers/{offer_id}/").data["question_count"] >= 20


def test_selection_without_official_topic_needs_the_key(client, settings):
    offer_id = analyze(client, settings)
    settings.ANTHROPIC_API_KEY = ""
    assert client.post(f"/api/offers/{offer_id}/generate/", {"requirements": ["Kafka"]}, format="json").status_code == 503
    assert client.post(f"/api/offers/{offer_id}/generate/", {"requirements": []}, format="json").status_code == 400


def finish_quiz(client, offer_id, wrong_for=()):
    attempt = client.post(f"/api/offers/{offer_id}/attempts/").data
    assert "level" not in attempt["question"]
    while attempt["status"] == "active":
        question = Question.objects.get(pk=attempt["question"]["id"])
        want_wrong = question.requirement in wrong_for
        choice = question.choices.get(is_correct=not want_wrong) if not want_wrong else question.choices.filter(is_correct=False).first()
        attempt = client.post(
            f"/api/offers/{offer_id}/attempts/{attempt['id']}/answer/", {"choice": choice.id}, format="json"
        ).data
        assert "correct" not in attempt
    return attempt


def test_all_correct_but_one_required_requirement_not_evaluated(client, settings):
    offer_id = analyze(client, settings)
    build(client, offer_id, ["Java", "AWS", "Spring Boot"], questions("Spring Boot", 10))
    result = finish_quiz(client, offer_id)["result"]
    assert result["accuracy"] == 100 and result["compatibility"] < 100
    by_name = {r["name"]: r for r in result["requirements"]}
    assert by_name["Kafka"]["evaluated"] is False and by_name["Kafka"]["met"] is False
    assert result["verdict"] == "compatible"  # Kafka es solo valorable
    assert "level" not in result


def test_required_requirement_left_out_makes_the_candidate_not_fully_compatible(client, settings):
    offer_id = analyze(client, settings)
    build(client, offer_id, ["Java", "AWS"])
    result = finish_quiz(client, offer_id)["result"]
    assert "Spring Boot" in result["missing_required"] and result["verdict"] == "partial"
    assert client.get(f"/api/offers/{offer_id}/").data["attempts"][0]["verdict"] == "partial"


def test_failing_a_required_requirement_lowers_compatibility(client, settings):
    offer_id = analyze(client, settings)
    build(client, offer_id, ["Java", "AWS", "Spring Boot"], questions("Spring Boot", 10))
    result = finish_quiz(client, offer_id, wrong_for=("Java", "AWS", "Spring Boot"))["result"]
    assert result["accuracy"] == 0 and result["verdict"] == "not_compatible"


def test_attempt_rules(client, settings):
    offer_id = analyze(client, settings)
    assert client.post(f"/api/offers/{offer_id}/attempts/").status_code == 409
    build(client, offer_id, ["Java", "AWS"])
    attempt = client.post(f"/api/offers/{offer_id}/attempts/").data
    again = client.post(f"/api/offers/{offer_id}/attempts/").data
    assert again["id"] == attempt["id"]
    other = Question.objects.filter(job_offer_id=offer_id).exclude(pk=attempt["question"]["id"]).first()
    bad = client.post(f"/api/offers/{offer_id}/attempts/{attempt['id']}/answer/", {"choice": other.choices.first().id}, format="json")
    assert bad.status_code == 400


def test_regenerating_replaces_questions_and_results(client, settings):
    offer_id = analyze(client, settings)
    build(client, offer_id, ["Java", "AWS"])
    finish_quiz(client, offer_id)
    build(client, offer_id, ["Java"])
    offer = client.get(f"/api/offers/{offer_id}/").data
    assert offer["attempts"] == [] and offer["selected_requirements"] == ["Java"]


@mock.patch("offers.ai.call_tool", side_effect=AITemporaryError("sin red"))
def test_temporary_error_marks_offer_as_failed_when_eager(call, client, settings):
    settings.ANTHROPIC_API_KEY = "test"
    offer_id = client.post("/api/offers/", {"raw_text": TEXT}, format="json").data["id"]
    assert JobOffer.objects.get(pk=offer_id).status == "failed"


def test_users_only_see_their_offers(client, user):
    from quiz.tests.helpers import api_for, make_user

    offer = JobOffer.objects.create(user=user, raw_text=TEXT, status="ready")
    assert api_for(make_user("otra")).get(f"/api/offers/{offer.id}/").status_code == 404


def test_compatibility_weights_required_90_and_optional_10():
    from offers.services import compatibility_score

    assert compatibility_score([1.0], [0.0]) == pytest.approx(0.9)
    assert compatibility_score([0.5], [1.0]) == pytest.approx(0.55)
    assert compatibility_score([0.5], []) == pytest.approx(0.5)
    assert compatibility_score([], [0.4]) == pytest.approx(0.4)


def test_question_count_is_20_or_40_only_with_more_than_three_requirements(client, settings):
    offer_id = analyze(client, settings)
    url = f"/api/offers/{offer_id}/generate/"
    assert client.post(url, {"requirements": ["Java", "AWS"], "count": 40}, format="json").status_code == 400
    assert client.post(url, {"requirements": ["Java", "AWS"], "count": 30}, format="json").status_code == 400
    assert client.post(url, {"requirements": ["Java", "AWS"], "count": 20}, format="json").status_code == 202


def test_forty_questions_when_more_than_three_requirements(client, settings):
    offer_id = analyze(client, settings)
    settings.ANTHROPIC_API_KEY = "test"
    with mock.patch("offers.ai.call_tool", return_value={"questions": questions("Spring Boot", 40) + questions("Kafka", 40)}):
        response = client.post(
            f"/api/offers/{offer_id}/generate/",
            {"requirements": ["Java", "AWS", "Spring Boot", "Kafka"], "count": 40}, format="json",
        )
    assert response.status_code == 202
    assert client.get(f"/api/offers/{offer_id}/").data["question_count"] >= 40


def test_finishing_recommends_official_topics_without_saving_them_and_gives_review(client, user, settings):
    offer_id = analyze(client, settings)
    build(client, offer_id, ["Java", "AWS", "Spring Boot"], questions("Spring Boot", 10))
    from accounts.models import get_profile

    get_profile(user).topics.clear()
    attempt = finish_quiz(client, offer_id, wrong_for=("AWS",))
    slugs = [t["slug"] for t in attempt["result"]["recommended_topics"]]
    assert slugs[0] == "aws-cloud" and set(slugs) == {"java", "aws-cloud"}
    assert attempt["result"]["recommended_topics"][0]["reinforce"] is True
    assert not get_profile(user).topics.exists()
    # el alumno decide si los añade a su biblioteca
    topic_id = attempt["result"]["recommended_topics"][0]["id"]
    assert client.post(f"/api/topics/{topic_id}/join/").status_code in (200, 201, 204)
    assert get_profile(user).topics.filter(pk=topic_id).exists()
    review = attempt["review"]
    assert len(review) == attempt["total"] and review[0]["choices"] and "explanation" in review[0]
    # la pregunta de una oferta sin tema se puede consultar al chatbot por su dueño
    assert client.get(f"/api/questions/{review[0]['id']}/").status_code in (200, 404)
