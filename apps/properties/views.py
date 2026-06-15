"""
ViewSet for Property Listings with filtering, search, and view tracking.
"""
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsOwnerOrReadOnly, IsRealtorOnly
from .filters import PropertyFilter
from .models import PropertyListing, PropertyImage, PropertyView
from .serializers import (
    PropertyListSerializer,
    PropertyDetailSerializer,
    PropertyCreateSerializer,
    PropertyImageSerializer,
    PropertyImageUploadSerializer,
)


class PropertyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on property listings.

    Endpoints:
      GET    /api/v1/properties/            → List (public, filtered, paginated)
      POST   /api/v1/properties/            → Create (realtors only)
      GET    /api/v1/properties/<id>/        → Detail (public, tracks views)
      PUT    /api/v1/properties/<id>/        → Update (owner only)
      PATCH  /api/v1/properties/<id>/        → Partial update (owner only)
      DELETE /api/v1/properties/<id>/        → Delete (owner only)
      POST   /api/v1/properties/<id>/images/ → Upload images (owner only)
    """
    filterset_class = PropertyFilter
    lookup_field = 'id'

    def get_queryset(self):
        """
        Optimized queryset with select_related and prefetch_related
        to prevent N+1 queries.
        """
        return (
            PropertyListing.objects
            .select_related('realtor__user')
            .prefetch_related('images')
            .all()
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return PropertyListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return PropertyCreateSerializer
        return PropertyDetailSerializer

    def get_permissions(self):
        """
        Dynamic permissions:
        - list/retrieve: public
        - create: authenticated realtors
        - update/delete: owner only
        """
        if self.action in ('list', 'retrieve', 'featured', 'upcoming'):
            return [permissions.AllowAny()]
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsRealtorOnly()]
        return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]

    def retrieve(self, request, *args, **kwargs):
        """
        GET single property — also tracks the view for analytics.
        """
        instance = self.get_object()

        # Track the view
        self._track_view(request, instance)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def _track_view(self, request, property_listing):
        """Record a property view for analytics. Deduplicate by IP per hour."""
        ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        from django.utils import timezone
        from datetime import timedelta
        one_hour_ago = timezone.now() - timedelta(hours=1)

        # Only count unique views per IP per hour
        recent_view = PropertyView.objects.filter(
            property_listing=property_listing,
            viewer_ip=ip,
            viewed_at__gte=one_hour_ago,
        ).exists()

        if not recent_view:
            PropertyView.objects.create(
                property_listing=property_listing,
                viewer_ip=ip,
                user_agent=user_agent,
            )
            # Increment denormalized counter
            PropertyListing.objects.filter(id=property_listing.id).update(
                view_count=models.F('view_count') + 1
            )

    def _get_client_ip(self, request):
        """Extract client IP from request, supporting proxies."""
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @action(detail=True, methods=['post'], url_path='images')
    def upload_images(self, request, id=None):
        """
        POST /api/v1/properties/<id>/images/
        Upload one or more images to a property listing.
        Only the property owner can upload images.
        """
        property_listing = self.get_object()

        # Verify ownership
        if property_listing.realtor.user != request.user:
            return Response(
                {'error': 'You can only upload images to your own listings.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        images = request.FILES.getlist('images')
        if not images:
            return Response(
                {'error': 'No images provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_images = []
        for image_file in images:
            img = PropertyImage.objects.create(
                property_listing=property_listing,
                image=image_file,
                caption=request.data.get('caption', ''),
            )
            created_images.append(img)

        # Set first as primary if no primary exists
        if not property_listing.images.filter(is_primary=True).exists() and created_images:
            created_images[0].is_primary = True
            created_images[0].save(update_fields=['is_primary'])

        serializer = PropertyImageSerializer(created_images, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my-listings')
    def my_listings(self, request):
        """
        GET /api/v1/properties/my-listings/
        Return all listings owned by the authenticated realtor.
        """
        if not hasattr(request.user, 'realtor_profile'):
            return Response(
                {'error': 'You do not have a realtor profile.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(realtor=request.user.realtor_profile)
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PropertyListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = PropertyListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        GET /api/v1/properties/featured/
        Return featured properties.
        """
        queryset = self.get_queryset().filter(is_featured=True, status='available')[:10]
        serializer = PropertyListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        GET /api/v1/properties/upcoming/
        Return upcoming estate properties.
        """
        queryset = self.get_queryset().filter(listing_type='upcoming', status='available')[:10]
        serializer = PropertyListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


# Need F expression for atomic counter update
from django.db import models  # noqa: E402
