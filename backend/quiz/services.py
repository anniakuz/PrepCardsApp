from django.db import transaction

from accounts.models import get_profile

from .models import Choice, Question, Topic


def add_questions(topic, parsed, language="en", job_offer=None):
    for item in parsed:
        question = Question.objects.create(
            topic=topic,
            level=item["level"],
            text=item["text"],
            explanation=item["explanation"],
            language=language,
            job_offer=job_offer,
        )
        Choice.objects.bulk_create(
            Choice(question=question, text=text, is_correct=(index == item["answer"]))
            for index, text in enumerate(item["choices"])
        )


@transaction.atomic
def create_topic(owner, name, description, parsed, uses_levels, language="en"):
    topic = Topic.objects.create(
        name=name, description=description, owner=owner, visibility="private", uses_levels=uses_levels
    )
    add_questions(topic, parsed, language)
    get_profile(owner).topics.add(topic)
    return topic


@transaction.atomic
def replace_questions(topic, parsed, uses_levels, language="en"):
    """Sustituye todas las preguntas. El tema vuelve a privado hasta que se verifique de nuevo."""
    topic.questions.all().delete()
    add_questions(topic, parsed, language)
    topic.uses_levels = uses_levels
    topic.visibility = "private"
    topic.publish_status = ""
    topic.publish_report = []
    topic.save()


def request_publication(topic):
    from .tasks import verify_topic_task

    topic.publish_status = "pending"
    topic.publish_report = []
    topic.save(update_fields=["publish_status", "publish_report"])
    verify_topic_task.delay(topic.id)
