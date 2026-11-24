import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

logger = logging.getLogger("prepcards.tasks")

WELCOME_SUBJECT = "Bienvenida a PrepCards"
WELCOME_BODY = """Hola {username}.

Tu cuenta de PrepCards ya está lista.

Empieza así.
1. Elige un tema en el catálogo y añádelo a Mis temas.
2. Haz tu primera ronda de 20 preguntas. Tu nivel sube o baja según cómo respondas.
3. Si quieres ayuda, pide a un mentor que te acompañe desde la sección Mentoría.

Entra aquí para empezar
{url}

Si no has creado tú esta cuenta, ignora este mensaje.
"""


@shared_task
def send_welcome_email(user_id):
    """Email de bienvenida. Más adelante se enviará desde el correo real del proyecto."""
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if not user or not user.email:
        return False
    send_mail(
        WELCOME_SUBJECT,
        WELCOME_BODY.format(username=user.username, url=settings.FRONTEND_URL),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    logger.info("welcome email sent user=%s", user.pk)
    return True
