from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "experience", "accepting_requests"]
    list_filter = ["role", "experience"]
    list_editable = ["role"]
    filter_horizontal = ["topics"]
    search_fields = ["user__username", "user__email"]
