from django.db.models import Q

from .models import Topic


def accessible_topics(user):
    """Temas oficiales, públicos, propios y los que un mentor ha compartido con el usuario."""
    shared = user.shared_topics.values("id")
    return Topic.objects.filter(
        Q(visibility__in=("official", "public")) | Q(owner=user) | Q(id__in=shared)
    )


def can_access_question(user, question):
    if question.topic_id is None:
        # Pregunta de un cuestionario de oferta. Solo la ve su dueño
        return question.job_offer_id is not None and question.job_offer.user_id == user.id
    if accessible_topics(user).filter(pk=question.topic_id).exists():
        return True
    # Una pregunta enviada por el chat se puede abrir aunque su tema no sea accesible
    from mentoring.models import Message

    return Message.objects.filter(question=question).filter(
        Q(enrollment__mentor=user) | Q(enrollment__student=user)
    ).exists()


def can_manage_topic(user, topic):
    from accounts.models import role_of

    if topic.owner_id is None:
        return role_of(user) == "admin"
    return topic.owner_id == user.id or role_of(user) == "admin"
