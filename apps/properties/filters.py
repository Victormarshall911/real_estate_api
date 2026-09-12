from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import models
from django_filters import rest_framework as filters
from .models import PropertyListing


class PropertyFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_size = filters.NumberFilter(field_name='land_size', lookup_expr='gte')
    max_size = filters.NumberFilter(field_name='land_size', lookup_expr='lte')
    location = filters.CharFilter(method='filter_location')
    search = filters.CharFilter(method='filter_search')
    status = filters.ChoiceFilter(choices=PropertyListing.Status.choices)
    state = filters.CharFilter(field_name='state', lookup_expr='icontains')
    property_category = filters.CharFilter(field_name='property_category')
    property_type = filters.CharFilter(field_name='property_type')
    bedrooms = filters.NumberFilter(field_name='bedrooms')
    bedrooms_gte = filters.NumberFilter(field_name='bedrooms', lookup_expr='gte')
    bathrooms = filters.NumberFilter(field_name='bathrooms')
    rent_frequency = filters.CharFilter(field_name='rent_frequency')
    state_ref = filters.NumberFilter(field_name='state_ref')
    lga_ref = filters.NumberFilter(field_name='lga_ref')
    verified_only = filters.BooleanFilter(method='filter_verified_only')

    class Meta:
        model = PropertyListing
        fields = [
            'min_price', 'max_price', 'min_size', 'max_size', 'location', 'search',
            'status', 'state', 'property_category', 'property_type', 'bedrooms',
            'bedrooms_gte', 'bathrooms', 'rent_frequency', 'state_ref', 'lga_ref',
            'verified_only'
        ]

    def filter_location(self, queryset, name, value):
        return queryset.filter(
            models.Q(location__icontains=value) | models.Q(state__icontains=value)
        )

    def filter_verified_only(self, queryset, name, value):
        if value:
            return queryset.filter(
                models.Q(is_title_verified=True) |
                models.Q(documents__is_verified=True) |
                models.Q(realtor__is_verified=True) |
                models.Q(landlord__is_verified=True) |
                models.Q(developer__is_verified=True)
            ).distinct()
        return queryset

    def filter_search(self, queryset, name, value):
        try:
            search_vector = SearchVector('title', weight='A') + SearchVector('description', weight='B')
            search_query = SearchQuery(value)
            return (
                queryset
                .annotate(rank=SearchRank(search_vector, search_query))
                .filter(rank__gte=0.1)
                .order_by('-rank')
            )
        except Exception:
            return queryset.filter(
                models.Q(title__icontains=value) | models.Q(description__icontains=value)
            )
