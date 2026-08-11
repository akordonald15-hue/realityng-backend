from django.contrib import admin

from apps.properties.models import (
    Favorite,
    Inquiry,
    Property,
    PropertyAssignment,
    PropertyImage,
    RentalApplication,
    Viewing,
)


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


@admin.register(PropertyAssignment)
class PropertyAssignmentAdmin(admin.ModelAdmin):
    list_display = ["property", "user", "relationship_type", "status", "assigned_by", "expires_at"]
    list_filter = ["relationship_type", "status", "expires_at", "created_at"]
    search_fields = ["property__title", "user__email", "assigned_by__email", "notes"]
    readonly_fields = ["created_at", "updated_at", "assigned_at", "accepted_at", "revoked_at"]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "property", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__email", "property__title", "property__city"]
    readonly_fields = ["created_at"]


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = [
        "property",
        "interested_user",
        "property_owner",
        "inquiry_type",
        "contact_preference",
        "status",
        "created_at",
    ]
    list_filter = ["status", "inquiry_type", "contact_preference", "created_at"]
    search_fields = [
        "property__title",
        "interested_user__email",
        "property_owner__email",
        "message",
        "internal_notes",
    ]
    readonly_fields = ["created_at", "updated_at", "deleted_at"]


@admin.register(Viewing)
class ViewingAdmin(admin.ModelAdmin):
    list_display = [
        "property",
        "requester",
        "property_owner",
        "viewing_type",
        "preferred_date",
        "preferred_time",
        "status",
        "created_at",
    ]
    list_filter = ["status", "viewing_type", "preferred_date", "created_at"]
    search_fields = [
        "property__title",
        "requester__email",
        "property_owner__email",
        "meeting_location",
        "notes",
    ]
    readonly_fields = ["created_at", "updated_at", "deleted_at"]


@admin.register(RentalApplication)
class RentalApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "property",
        "applicant",
        "property_owner",
        "full_name",
        "employment_status",
        "move_in_date",
        "status",
        "created_at",
    ]
    list_filter = ["status", "employment_status", "move_in_date", "created_at"]
    search_fields = [
        "property__title",
        "applicant__email",
        "property_owner__email",
        "full_name",
        "email",
        "phone",
        "employer_name",
        "message",
        "owner_notes",
    ]
    readonly_fields = ["created_at", "updated_at", "deleted_at"]
