from django_filters import rest_framework as filters

from apps.properties.choices import ListingType, PropertyType
from apps.properties.models import Property


class PublicPropertyFilter(filters.FilterSet):
    state = filters.CharFilter(field_name="state", lookup_expr="iexact")
    city = filters.CharFilter(field_name="city", lookup_expr="iexact")
    lga = filters.CharFilter(field_name="lga", lookup_expr="iexact")
    neighborhood = filters.CharFilter(field_name="neighborhood", lookup_expr="icontains")
    property_type = filters.ChoiceFilter(choices=PropertyType.choices)
    listing_type = filters.ChoiceFilter(choices=ListingType.choices)
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    min_bedrooms = filters.NumberFilter(field_name="bedrooms", lookup_expr="gte")
    min_bathrooms = filters.NumberFilter(field_name="bathrooms", lookup_expr="gte")
    min_lat = filters.NumberFilter(field_name="latitude", lookup_expr="gte")
    max_lat = filters.NumberFilter(field_name="latitude", lookup_expr="lte")
    min_lng = filters.NumberFilter(field_name="longitude", lookup_expr="gte")
    max_lng = filters.NumberFilter(field_name="longitude", lookup_expr="lte")
    has_map_location = filters.BooleanFilter(method="filter_has_map_location")

    def filter_has_map_location(self, queryset, name, value):
        if value:
            return queryset.filter(latitude__isnull=False, longitude__isnull=False).exclude(
                location_precision="hidden"
            )
        return queryset

    class Meta:
        model = Property
        fields = [
            "state",
            "city",
            "lga",
            "neighborhood",
            "property_type",
            "listing_type",
            "min_price",
            "max_price",
            "min_bedrooms",
            "min_bathrooms",
            "min_lat",
            "max_lat",
            "min_lng",
            "max_lng",
            "has_map_location",
        ]
