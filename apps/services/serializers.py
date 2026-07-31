from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.services.choices import ProviderStatus, ProviderTradeStatus
from apps.services.models import ProviderTrade, ServiceArea, ServiceProvider, TradeCategory


class TradeCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = TradeCategory
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "description",
            "icon",
            "display_order",
            "requires_certification",
            "is_active",
            "children",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, obj):
        children = [
            child for child in getattr(obj, "prefetched_children", []) if child.is_active
        ]
        if not children and not hasattr(obj, "prefetched_children"):
            children = obj.children.filter(is_active=True)
        return TradeCategorySerializer(children, many=True, context=self.context).data


class ProviderTradeSerializer(serializers.ModelSerializer):
    category = TradeCategorySerializer(read_only=True)

    class Meta:
        model = ProviderTrade
        fields = [
            "id",
            "category",
            "is_primary",
            "years_experience",
            "skill_level",
        ]
        read_only_fields = fields


class ServiceAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceArea
        fields = [
            "id",
            "country",
            "state",
            "city",
            "lga",
            "neighborhood",
            "service_radius_km",
        ]
        read_only_fields = fields


class PublicServiceProviderListSerializer(serializers.ModelSerializer):
    trades = serializers.SerializerMethodField()
    primary_trade = serializers.SerializerMethodField()
    service_areas = ServiceAreaSerializer(many=True, read_only=True)
    display_location = serializers.CharField(source="public_display_location", read_only=True)
    verification_badges = serializers.SerializerMethodField()

    class Meta:
        model = ServiceProvider
        fields = [
            "id",
            "slug",
            "provider_type",
            "business_name",
            "headline",
            "biography",
            "phone",
            "email",
            "country",
            "state",
            "city",
            "lga",
            "neighborhood",
            "display_location",
            "verification_badges",
            "average_rating",
            "completed_jobs_count",
            "trades",
            "primary_trade",
            "service_areas",
            "created_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_trades(self, obj):
        trades = [
            trade
            for trade in obj.trades.all()
            if trade.status == ProviderTradeStatus.ACTIVE
            and trade.category.is_active
            and not trade.category.deleted_at
        ]
        return ProviderTradeSerializer(trades, many=True, context=self.context).data

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_primary_trade(self, obj):
        primary = next(
            (
                trade
                for trade in obj.trades.all()
                if trade.is_primary
                and trade.status == ProviderTradeStatus.ACTIVE
                and trade.category.is_active
                and not trade.category.deleted_at
            ),
            None,
        )
        return ProviderTradeSerializer(primary, context=self.context).data if primary else None

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_verification_badges(self, obj):
        snapshot = obj.verification_snapshot or {}
        badges = snapshot.get("badges", [])
        if isinstance(badges, list):
            return badges
        return []


class PublicServiceProviderDetailSerializer(PublicServiceProviderListSerializer):
    portfolio = serializers.SerializerMethodField()
    reviews_summary = serializers.SerializerMethodField()

    class Meta(PublicServiceProviderListSerializer.Meta):
        fields = PublicServiceProviderListSerializer.Meta.fields + [
            "portfolio",
            "reviews_summary",
        ]

    @extend_schema_field(serializers.DictField())
    def get_portfolio(self, obj):
        return {
            "items": [],
            "message": "Portfolio uploads will be available in Sprint 9.2.",
        }

    @extend_schema_field(serializers.DictField())
    def get_reviews_summary(self, obj):
        return {
            "average_rating": str(obj.average_rating),
            "completed_jobs_count": obj.completed_jobs_count,
            "review_count": 0,
            "message": "Verified booking reviews will be available in a later Sprint 9 phase.",
        }


def active_public_provider_queryset():
    return (
        ServiceProvider.objects.filter(status=ProviderStatus.ACTIVE)
        .select_related("user")
        .prefetch_related("trades__category", "service_areas")
    )
