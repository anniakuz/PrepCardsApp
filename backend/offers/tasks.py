import logging

from celery import shared_task

from config.ai_client import retry_or_none as _retry_or_none

from . import ai
from .models import JobOffer
from .services import clean_level, clean_requirements, plan, quiz_level, save_offer_questions

logger = logging.getLogger("prepcards.tasks")
MAX_RETRIES = 3


@shared_task(bind=True, max_retries=MAX_RETRIES)
def analyze_offer_task(self, offer_id):
    offer = JobOffer.objects.filter(pk=offer_id).first()
    if not offer:
        return
    try:
        data = ai.analyze_offer(offer.raw_text)
    except ai.AITemporaryError as exc:
        retry = _retry_or_none(self, exc)
        if retry:
            _note(offer, "error", self)
            raise retry
        return _fail(offer, "status", "error", exc)
    except ai.AIUnavailable as exc:
        return _fail(offer, "status", "error", exc)

    requirements = clean_requirements(data.get("requirements"))
    if data.get("valid") is False or not requirements:
        offer.status = "invalid"
        offer.error = (data.get("problem") or "No se ha encontrado ningún requisito técnico concreto.")[:500]
        offer.save(update_fields=["status", "error"])
        logger.info("offer invalid id=%s", offer.pk)
        return

    offer.title = (data.get("title") or "")[:200]
    offer.company = (data.get("company") or "")[:200]
    offer.summary = data.get("summary") or ""
    offer.requirements = requirements
    offer.level = clean_level(data.get("level"))
    offer.level_reason = (data.get("level_reason") or "")[:200] if offer.level else ""
    offer.status = "ready"
    offer.error = ""
    offer.save()
    logger.info("offer analyzed id=%s requirements=%s", offer.pk, len(offer.requirements))


@shared_task(bind=True, max_retries=MAX_RETRIES)
def generate_questions_task(self, offer_id, selected, count=20):
    offer = JobOffer.objects.filter(pk=offer_id).first()
    if not offer:
        return
    steps = plan(offer, selected, count)
    items = []
    if steps["needs"]:
        try:
            items = ai.generate_questions(offer, steps["needs"], quiz_level(offer))
        except ai.AITemporaryError as exc:
            retry = _retry_or_none(self, exc)
            if retry:
                _note(offer, "generation_error", self)
                raise retry
            return _fail(offer, "generation_status", "generation_error", exc)
        except ai.AIUnavailable as exc:
            return _fail(offer, "generation_status", "generation_error", exc)

    created = save_offer_questions(offer, steps["picks"], items, "es")
    offer.generation_status = "done"
    offer.generation_error = ""
    offer.last_generated = created
    offer.selected_requirements = list(selected)
    offer.save(update_fields=["generation_status", "generation_error", "last_generated", "selected_requirements"])
    logger.info("quiz built offer=%s questions=%s official=%s", offer.pk, created, len(steps["picks"]))


def _note(offer, field, task):
    """Aviso mientras se reintenta, para que la pantalla no parezca bloqueada."""
    setattr(offer, field, f"La IA está saturada (límite de uso). Reintentando, intento {task.request.retries + 2} de {MAX_RETRIES + 1}")
    offer.save(update_fields=[field])


def _fail(offer, status_field, error_field, exc):
    setattr(offer, status_field, "failed")
    setattr(offer, error_field, str(exc))
    offer.save(update_fields=[status_field, error_field])
    logger.warning("offer task failed id=%s error=%s", offer.pk, exc)
