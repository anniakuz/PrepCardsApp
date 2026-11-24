from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from accounts.models import get_profile

from .models import Message


def group_name(enrollment_id):
    return f"chat_{enrollment_id}"


def message_payload(message):
    question = message.question
    topic = message.topic
    return {
        "id": message.id,
        "sender": message.sender_id,
        "sender_name": message.sender.username,
        "text": message.text,
        "question": {"id": question.id, "text": question.text, "level": question.level} if question else None,
        "topic": {"id": topic.id, "name": topic.name} if topic else None,
        "created_at": message.created_at.isoformat(),
    }


@transaction.atomic
def create_message(enrollment, sender, text="", question=None, topic=None):
    message = Message.objects.create(enrollment=enrollment, sender=sender, text=text, question=question, topic=topic)
    if topic is not None:
        # El mentor comparte el tema privado con el estudiante y se añade a sus temas
        topic.shared_with.add(enrollment.student)
        get_profile(enrollment.student).topics.add(topic)
    return message


def broadcast(message):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        group_name(message.enrollment_id), {"type": "chat.message", "message": message_payload(message)}
    )
