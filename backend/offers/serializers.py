from rest_framework import serializers

from .models import JobOffer
from .services import suggested_topics


class OfferSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    suggested_topics = serializers.SerializerMethodField()
    attempts = serializers.SerializerMethodField()

    class Meta:
        model = JobOffer
        fields = [
            "id", "title", "company", "raw_text", "summary", "requirements", "level", "level_reason",
            "selected_requirements", "suggested_topics", "status", "error", "generation_status",
            "generation_error", "question_count", "attempts", "created_at",
        ]

    def get_question_count(self, obj):
        return obj.questions.count()

    def get_suggested_topics(self, obj):
        return [{"id": t.id, "name": t.name, "slug": t.slug} for t in suggested_topics(obj)]

    def get_attempts(self, obj):
        user = self.context["request"].user if self.context.get("request") else obj.user
        finished = obj.attempts.filter(user=user, status="finished")[:10]
        return [
            {"id": a.id, "finished_at": a.finished_at, "accuracy": a.result.get("accuracy"),
             "compatibility": a.result.get("compatibility"), "verdict": a.result.get("verdict")}
            for a in finished
        ]
