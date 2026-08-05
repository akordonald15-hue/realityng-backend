from django.contrib import admin

from apps.services.models import (
    PortfolioImage,
    ProviderTrade,
    QuoteRequest,
    ServiceArea,
    ServiceBooking,
    ServiceProvider,
    ServiceReview,
    ServiceReviewFlag,
    TradeCategory,
)


class ProviderTradeInline(admin.TabularInline):
    model = ProviderTrade
    extra = 0
    autocomplete_fields = ["category"]


class ServiceAreaInline(admin.TabularInline):
    model = ServiceArea
    extra = 0


class PortfolioImageInline(admin.TabularInline):
    model = PortfolioImage
    extra = 0
    autocomplete_fields = ["category"]


@admin.register(TradeCategory)
class TradeCategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "parent",
        "slug",
        "requires_certification",
        "is_active",
        "display_order",
    ]
    list_filter = ["is_active", "requires_certification", "parent"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["display_order", "name"]


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    inlines = [ProviderTradeInline, ServiceAreaInline, PortfolioImageInline]
    list_display = [
        "business_name",
        "provider_type",
        "status",
        "state",
        "city",
        "average_rating",
        "completed_jobs_count",
        "submitted_at",
        "published_at",
    ]
    list_filter = ["provider_type", "status", "state", "city"]
    search_fields = ["business_name", "headline", "biography", "user__email"]
    prepopulated_fields = {"slug": ("business_name",)}
    autocomplete_fields = ["user", "reviewed_by"]
    ordering = ["business_name"]


@admin.register(ProviderTrade)
class ProviderTradeAdmin(admin.ModelAdmin):
    list_display = [
        "provider",
        "category",
        "is_primary",
        "years_experience",
        "skill_level",
        "status",
    ]
    list_filter = ["is_primary", "skill_level", "status", "category"]
    search_fields = ["provider__business_name", "category__name"]
    autocomplete_fields = ["provider", "category"]


@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = [
        "provider",
        "state",
        "city",
        "lga",
        "neighborhood",
        "service_radius_km",
        "is_primary",
    ]
    list_filter = ["state", "city", "lga", "is_primary"]
    search_fields = ["provider__business_name", "state", "city", "lga", "neighborhood"]
    autocomplete_fields = ["provider"]


@admin.register(PortfolioImage)
class PortfolioImageAdmin(admin.ModelAdmin):
    list_display = ["provider", "caption", "category", "display_order", "is_cover", "status"]
    list_filter = ["status", "is_cover", "category"]
    search_fields = ["provider__business_name", "caption"]
    autocomplete_fields = ["provider", "category"]


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = [
        "project_title",
        "provider",
        "customer_name",
        "status",
        "preferred_contact_method",
        "state",
        "created_at",
    ]
    list_filter = ["status", "preferred_contact_method", "state", "created_at"]
    search_fields = [
        "project_title",
        "project_description",
        "customer_name",
        "phone",
        "email",
        "provider__business_name",
    ]
    autocomplete_fields = ["customer", "provider", "service_category"]
    readonly_fields = ["created_at", "updated_at", "deleted_at"]


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "provider",
        "customer",
        "status",
        "service_category",
        "completed_at",
        "created_at",
    ]
    list_filter = ["status", "service_category", "created_at", "completed_at"]
    search_fields = [
        "title",
        "service_summary",
        "provider__business_name",
        "customer__email",
    ]
    autocomplete_fields = ["quote_request", "customer", "provider", "service_category"]
    readonly_fields = ["created_at", "updated_at", "deleted_at"]


@admin.register(ServiceReview)
class ServiceReviewAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "provider",
        "customer",
        "rating",
        "status",
        "would_recommend",
        "published_at",
        "created_at",
    ]
    list_filter = ["status", "rating", "would_recommend", "created_at", "published_at"]
    search_fields = [
        "title",
        "comment",
        "provider_response",
        "moderation_reason",
        "provider__business_name",
        "customer__email",
    ]
    autocomplete_fields = ["booking", "customer", "provider"]
    readonly_fields = [
        "creation_ip",
        "user_agent",
        "created_at",
        "updated_at",
        "deleted_at",
    ]


@admin.register(ServiceReviewFlag)
class ServiceReviewFlagAdmin(admin.ModelAdmin):
    list_display = ["review", "user", "reason", "created_at"]
    list_filter = ["reason", "created_at"]
    search_fields = ["details", "review__title", "user__email"]
    autocomplete_fields = ["review", "user"]
    readonly_fields = ["created_at", "updated_at", "deleted_at"]
