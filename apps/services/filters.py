from django_filters import rest_framework as filters

from apps.services.choices import ProviderType
from apps.services.models import ServiceProvider


class PublicServiceProviderFilter(filters.FilterSet):
    category = filters.CharFilter(method="filter_category")
    state = filters.CharFilter(field_name="state", lookup_expr="iexact")
    city = filters.CharFilter(field_name="city", lookup_expr="iexact")
    lga = filters.CharFilter(field_name="lga", lookup_expr="iexact")
    provider_type = filters.ChoiceFilter(choices=ProviderType.choices)

    def filter_category(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(trades__category__slug=value, trades__status="active").distinct()

    class Meta:
        model = ServiceProvider
        fields = ["category", "state", "city", "lga", "provider_type"]
