from django.contrib import admin

from apps.properties.models import Property


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "property_type",
        "listing_type",
        "price",
        "city",
        "status",
        "featured",
        "owner",
        "created_at",
    ]
    list_filter = ["status", "property_type", "listing_type", "featured", "state", "city"]
    search_fields = ["title", "description", "city", "owner__email"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["created_at", "updated_at", "deleted_at"]
