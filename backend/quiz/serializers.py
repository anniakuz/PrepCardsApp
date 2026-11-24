from rest_framework import serializers

from .models import AssistantMessage, Choice, Question, Topic


class TopicSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True, default=None)
    question_count = serializers.IntegerField(read_only=True, default=0)
    learners = serializers.IntegerField(read_only=True, default=0)
    mine = serializers.SerializerMethodField()
    is_mine_to_practice = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            "id", "name", "label", "description", "visibility", "uses_levels", "owner_name",
            "publish_status", "publish_report", "question_count", "learners", "mine", "is_mine_to_practice",
        ]

    def get_mine(self, obj):
        return obj.owner_id is not None and obj.owner_id == self.context["request"].user.id

    def get_is_mine_to_practice(self, obj):
        return obj.id in self.context.get("my_topic_ids", ())


class ChoicePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text"]


class ChoiceFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text", "is_correct"]


class QuestionSerializer(serializers.ModelSerializer):
    """Pregunta sin revelar la respuesta correcta."""

    topic_name = serializers.SerializerMethodField()
    choices = ChoicePublicSerializer(many=True, read_only=True)
    saved = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ["id", "topic", "topic_name", "level", "text", "language", "choices", "saved"]

    def get_topic_name(self, obj):
        if obj.topic_id:
            return obj.topic.label
        return f"Cuestionario de oferta: {obj.job_offer.title}" if obj.job_offer_id else ""

    def get_saved(self, obj):
        return obj.id in self.context.get("saved_ids", ())


class QuestionDetailSerializer(QuestionSerializer):
    """Pregunta con respuesta y explicación. Solo para quien ya ha respondido o la guardó."""

    choices = ChoiceFullSerializer(many=True, read_only=True)

    class Meta(QuestionSerializer.Meta):
        fields = QuestionSerializer.Meta.fields + ["explanation"]


class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantMessage
        fields = ["id", "role", "text", "created_at"]
