from django_filters import rest_framework as filters

from apps.properties.choices import ListingType, PropertyType
from apps.properties.models import Property


class PublicPropertyFilter(filters.FilterSet):
    city = filters.CharFilter(field_name="city", lookup_expr="iexact")
    property_type = filters.ChoiceFilter(choices=PropertyType.choices)
    listing_type = filters.ChoiceFilter(choices=ListingType.choices)
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Property
        fields = ["city", "property_type", "listing_type", "min_price", "max_price"]
