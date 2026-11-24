from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import Review, Topic, TopicProgress

EVOLUTION_LIMIT = 60


def build_stats(user, topic_id=None):
    reviews = Review.objects.filter(user=user)
    if topic_id:
        reviews = reviews.filter(question__topic_id=topic_id)

    totals = reviews.aggregate(total=Count("id"), correct=Count("id", filter=Q(is_correct=True)))
    since = timezone.now() - timedelta(days=13)
    daily = {
        row["day"]: row
        for row in reviews.filter(created_at__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"), correct=Count("id", filter=Q(is_correct=True)))
    }
    today = timezone.localdate()
    days = []
    for offset in range(13, -1, -1):
        day = today - timedelta(days=offset)
        row = daily.get(day, {})
        days.append({"date": day.isoformat(), "total": row.get("total", 0), "correct": row.get("correct", 0)})

    progress = {p.topic_id: p for p in TopicProgress.objects.filter(user=user)}
    per_topic = {
        row["question__topic_id"]: row
        for row in reviews.values("question__topic_id").annotate(
            total=Count("id"), correct=Count("id", filter=Q(is_correct=True))
        )
    }
    topics = []
    for topic in Topic.objects.filter(pk__in=set(progress) | set(per_topic)).select_related("owner"):
        row = per_topic.get(topic.id, {})
        current = progress.get(topic.id)
        evolution = list(
            Review.objects.filter(user=user, question__topic=topic, level_after__isnull=False)
            .order_by("-created_at", "-id")
            .values_list("level_after", flat=True)[:EVOLUTION_LIMIT]
        )[::-1]
        topics.append({
            "id": topic.id,
            "name": topic.label,
            "uses_levels": topic.uses_levels,
            "total": row.get("total", 0),
            "correct": row.get("correct", 0),
            "level": current.level if current and topic.uses_levels else None,
            "max_level": current.max_level if current and topic.uses_levels else None,
            "evolution": evolution if topic.uses_levels else [],
        })
    topics.sort(key=lambda t: (-t["total"], t["name"]))
    return {"total": totals["total"], "correct": totals["correct"], "days": days, "topics": topics}
