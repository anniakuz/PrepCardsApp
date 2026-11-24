from django.contrib import admin

from .models import (
    AssistantMessage,
    Choice,
    Question,
    QuestionAudit,
    Review,
    Round,
    SavedQuestion,
    Topic,
    TopicProgress,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    max_num = 4


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["label", "visibility", "publish_status", "uses_levels", "created_at"]
    list_filter = ["visibility", "publish_status"]
    search_fields = ["name", "owner__username"]
    filter_horizontal = ["shared_with"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["text", "topic", "level", "language"]
    list_filter = ["topic", "level", "language"]
    search_fields = ["text"]
    inlines = [ChoiceInline]


@admin.register(QuestionAudit)
class QuestionAuditAdmin(admin.ModelAdmin):
    list_display = ["question_id", "action", "changed_at"]
    readonly_fields = ["question_id", "action", "old_text", "changed_at"]


admin.site.register(TopicProgress)
admin.site.register(Round)
admin.site.register(Review)
admin.site.register(SavedQuestion)
admin.site.register(AssistantMessage)
