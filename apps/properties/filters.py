"""
Filters for property listings using django-filter and PostgreSQL full-text search.
"""
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django_filters import rest_framework as filters

from .models import PropertyListing


class PropertyFilter(filters.FilterSet):
    """
    Filterset for PropertyListing supporting:
    - min_price / max_price range
    - min_size (minimum land size in sqm)
    - location (partial match on location or state)
    - search (full-text search on title + description via PostgreSQL)
    - status (available / sold)
    """
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_size = filters.NumberFilter(field_name='land_size', lookup_expr='gte')
    max_size = filters.NumberFilter(field_name='land_size', lookup_expr='lte')
    location = filters.CharFilter(method='filter_location')
    search = filters.CharFilter(method='filter_search')
    status = filters.ChoiceFilter(choices=PropertyListing.Status.choices)
    state = filters.CharFilter(field_name='state', lookup_expr='icontains')

    class Meta:
        model = PropertyListing
        fields = ['min_price', 'max_price', 'min_size', 'max_size', 'location', 'search', 'status', 'state']

    def filter_location(self, queryset, name, value):
        """Filter by location or state (case-insensitive partial match)."""
        return queryset.filter(
            models.Q(location__icontains=value) | models.Q(state__icontains=value)
        )

    def filter_search(self, queryset, name, value):
        """
        Full-text search using PostgreSQL SearchVector.
        Falls back to icontains for SQLite in development.
        """
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
            # Fallback for SQLite (development)
            return queryset.filter(
                models.Q(title__icontains=value) | models.Q(description__icontains=value)
            )


# Import models.Q for the filter methods
from django.db import models  # noqa: E402
