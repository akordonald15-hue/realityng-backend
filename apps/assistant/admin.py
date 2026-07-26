from django.contrib import admin

from apps.assistant.models import AIConversation, AIMessage


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "provider", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("id", "user__email", "title")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("id", "conversation__id", "content")
    readonly_fields = ("id", "created_at", "updated_at")
