from django.contrib import admin

from apps.properties.models import Property, PropertyImage


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0
    fields = ["image", "caption", "display_order", "is_cover", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]
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


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ["property", "caption", "display_order", "is_cover", "created_at"]
    list_filter = ["is_cover", "created_at"]
    search_fields = ["property__title", "caption"]
    readonly_fields = ["created_at"]
