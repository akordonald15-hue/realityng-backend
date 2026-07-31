from django.contrib import admin

from apps.services.models import ProviderTrade, ServiceArea, ServiceProvider, TradeCategory


class ProviderTradeInline(admin.TabularInline):
    model = ProviderTrade
    extra = 0
    autocomplete_fields = ["category"]


class ServiceAreaInline(admin.TabularInline):
    model = ServiceArea
    extra = 0


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
    inlines = [ProviderTradeInline, ServiceAreaInline]
    list_display = [
        "business_name",
        "provider_type",
        "status",
        "state",
        "city",
        "average_rating",
        "completed_jobs_count",
    ]
    list_filter = ["provider_type", "status", "state", "city"]
    search_fields = ["business_name", "headline", "biography", "user__email"]
    prepopulated_fields = {"slug": ("business_name",)}
    autocomplete_fields = ["user"]
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
    list_display = ["provider", "state", "city", "lga", "neighborhood", "service_radius_km"]
    list_filter = ["state", "city", "lga"]
    search_fields = ["provider__business_name", "state", "city", "lga", "neighborhood"]
    autocomplete_fields = ["provider"]
