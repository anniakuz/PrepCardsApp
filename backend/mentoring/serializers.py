from rest_framework import serializers

from accounts.models import get_profile
from accounts.serializers import UserBriefSerializer

from .models import Enrollment
from .services import message_payload


class MentorSerializer(UserBriefSerializer):
    about = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    relation = serializers.SerializerMethodField()
    technologies = serializers.SerializerMethodField()

    class Meta(UserBriefSerializer.Meta):
        fields = ["id", "username", "about", "experience", "relation", "technologies"]

    def get_technologies(self, obj):
        names = set(get_profile(obj).topics.values_list("name", flat=True))
        names.update(obj.created_topics.filter(visibility__in=["public", "official"]).values_list("name", flat=True))
        return sorted(names)

    def get_about(self, obj):
        return get_profile(obj).about

    def get_experience(self, obj):
        return get_profile(obj).experience

    def get_relation(self, obj):
        return self.context.get("relations", {}).get(obj.id)


class EnrollmentSerializer(serializers.ModelSerializer):
    mentor = UserBriefSerializer(read_only=True)
    student = UserBriefSerializer(read_only=True)
    as_role = serializers.SerializerMethodField()
    share_data = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            "id", "mentor", "student", "status", "request_message", "share_stats", "share_answers", "share_data",
            "as_role", "created_at", "updated_at",
        ]

    def get_share_data(self, obj):
        return obj.share_stats and obj.share_answers

    def get_as_role(self, obj):
        return "mentor" if obj.mentor_id == self.context["request"].user.id else "student"


def serialize_message(message):
    return message_payload(message)
