"""
ViewSet for Property Listings with filtering, search, and view tracking.
"""
import uuid
from django.db import models
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsOwnerOrReadOnly, IsRealtorOnly, CanListProperties
from .filters import PropertyFilter
from .models import PropertyListing, PropertyImage, PropertyView, State, LGA, PropertyDocument, VerificationRequest, PropertyAnalyticsEvent, SavedSearch
from .serializers import (
    PropertyListSerializer,
    PropertyDetailSerializer,
    PropertyCreateSerializer,
    PropertyImageSerializer,
    PropertyImageUploadSerializer,
    StateSerializer,
    LGASerializer,
    PropertyDocumentSerializer,
    VerificationRequestSerializer,
    SavedSearchSerializer,
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
            .select_related('realtor__user', 'landlord__user', 'developer__user', 'state_ref', 'lga_ref')
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
        - create: authenticated sellers (realtors, landlords, developers)
        - request_verification/my_verifications: authenticated users
        - upload_document/update/delete: owner only
        """
        if self.action in ('list', 'retrieve', 'featured', 'upcoming'):
            return [permissions.AllowAny()]
        if self.action == 'create':
            return [permissions.IsAuthenticated(), CanListProperties()]
        if self.action in ('request_verification', 'my_verifications'):
            return [permissions.IsAuthenticated()]
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
        owner_user = None
        if property_listing.realtor:
            owner_user = property_listing.realtor.user
        elif property_listing.landlord:
            owner_user = property_listing.landlord.user
        elif property_listing.developer:
            owner_user = property_listing.developer.user

        if owner_user != request.user:
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
        Return all listings owned by the authenticated seller (realtor, landlord, or developer).
        """
        user = request.user
        queryset = self.get_queryset()
        if user.role == 'realtor' and hasattr(user, 'realtor_profile'):
            queryset = queryset.filter(realtor=user.realtor_profile)
        elif user.role == 'landlord' and hasattr(user, 'landlord_profile'):
            queryset = queryset.filter(landlord=user.landlord_profile)
        elif user.role == 'developer' and hasattr(user, 'developer_profile'):
            queryset = queryset.filter(developer=user.developer_profile)
        else:
            return Response(
                {'error': 'You do not have a seller profile.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
        queryset = self.get_queryset().filter(property_type='estate', status='available')[:10]
        serializer = PropertyListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='upload-document', permission_classes=[permissions.IsAuthenticated])
    def upload_document(self, request, id=None):
        """
        POST /api/v1/properties/<id>/upload-document/
        Allows the listing owner to upload a legal document.
        """
        property_listing = self.get_object()
        user = request.user
        is_owner = False
        if property_listing.realtor and property_listing.realtor.user == user:
            is_owner = True
        elif property_listing.landlord and property_listing.landlord.user == user:
            is_owner = True
        elif property_listing.developer and property_listing.developer.user == user:
            is_owner = True
            
        if not is_owner and not user.is_staff:
            return Response(
                {"error": "Only the listing owner can upload legal documents."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        document_type = request.data.get('document_type')
        uploaded_file = request.FILES.get('file')
        
        if not document_type or not uploaded_file:
            return Response(
                {"error": "Both 'document_type' and 'file' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if document_type not in PropertyDocument.DocumentType.values:
            return Response(
                {"error": f"Invalid document_type. Must be one of: {PropertyDocument.DocumentType.values}"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        doc = PropertyDocument.objects.create(
            property_listing=property_listing,
            document_type=document_type,
            file=uploaded_file
        )
        
        serializer = PropertyDocumentSerializer(doc, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='request-verification', permission_classes=[permissions.IsAuthenticated])
    def request_verification(self, request, id=None):
        """
        POST /api/v1/properties/<id>/request-verification/
        Request platform legal verification on this listing for ₦10,000.
        """
        property_listing = self.get_object()
        user = request.user
        
        existing = VerificationRequest.objects.filter(
            property_listing=property_listing,
            requester=user,
            status__in=['pending', 'in_progress']
        ).first()
        if existing:
            return Response(
                {"error": "You already have a pending title verification request for this property."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not property_listing.documents.exists():
            return Response(
                {"error": "No legal documents have been uploaded for this property yet. A title search cannot be requested without documents."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        from wallets.models import Wallet, WalletTransaction
        wallet, _ = Wallet.objects.get_or_create(user=user)
        fee = 10000.00
        
        if wallet.balance < fee:
            return Response(
                {"error": "Insufficient wallet balance to cover the ₦10,000 verification fee. Please deposit funds first."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        wallet.balance -= models.DecimalField().to_python(fee)
        wallet.save()
        
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='payment',
            amount=fee,
            reference=f"title_verify_{property_listing.id}_{uuid.uuid4().hex[:6]}",
            description=f"Paid fee for Title Verification on listing: {property_listing.title}"
        )
        
        req = VerificationRequest.objects.create(
            requester=user,
            property_listing=property_listing,
            fee_charged=fee
        )
        
        serializer = VerificationRequestSerializer(req, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my-verifications', permission_classes=[permissions.IsAuthenticated])
    def my_verifications(self, request):
        """
        GET /api/v1/properties/my-verifications/
        Returns list of verification requests submitted by the logged-in user.
        """
        queryset = VerificationRequest.objects.filter(requester=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = VerificationRequestSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = VerificationRequestSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='track-event', permission_classes=[permissions.AllowAny])
    def track_event(self, request, pk=None):
        """
        POST /api/v1/properties/<id>/track-event/
        Tracks an analytical event (view, whatsapp_click, phone_click, escrow_propose).
        """
        property_obj = self.get_object()
        event_type = request.data.get('event_type', 'view')
        valid_events = [choice[0] for choice in PropertyAnalyticsEvent.EventType.choices]
        if event_type not in valid_events:
            event_type = 'view'

        if event_type == 'view':
            PropertyListing.objects.filter(pk=property_obj.pk).update(view_count=models.F('view_count') + 1)

        PropertyAnalyticsEvent.objects.create(
            property_listing=property_obj,
            event_type=event_type,
            viewer=request.user if request.user.is_authenticated else None,
        )
        return Response({'status': 'tracked', 'event_type': event_type}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my-analytics', permission_classes=[permissions.IsAuthenticated])
    def my_analytics(self, request):
        """
        GET /api/v1/properties/my-analytics/
        Returns aggregated views, inquiries, and 14-day daily trends for the logged-in seller/realtor.
        """
        from django.utils import timezone
        import datetime

        user = request.user
        qs = PropertyListing.objects.filter(
            models.Q(realtor__user=user) | models.Q(landlord__user=user) | models.Q(developer__user=user)
        ).distinct()

        total_properties = qs.count()
        total_views = sum(p.view_count for p in qs)

        events_qs = PropertyAnalyticsEvent.objects.filter(property_listing__in=qs)
        total_whatsapp_clicks = events_qs.filter(event_type='whatsapp_click').count()
        total_phone_clicks = events_qs.filter(event_type='phone_click').count()
        total_inquiries = total_whatsapp_clicks + total_phone_clicks + events_qs.filter(event_type='escrow_propose').count()

        # 14-day timeline
        today = timezone.now().date()
        daily_trends = []
        for i in range(13, -1, -1):
            day = today - datetime.timedelta(days=i)
            day_events = events_qs.filter(created_at__date=day)
            views_count = day_events.filter(event_type='view').count()
            leads_count = day_events.exclude(event_type='view').count()
            daily_trends.append({
                'date': day.strftime('%Y-%m-%d'),
                'label': day.strftime('%b %d'),
                'views': views_count,
                'leads': leads_count,
            })

        # Property breakdown
        property_breakdown = []
        for p in qs[:15]:
            p_events = events_qs.filter(property_listing=p)
            wa = p_events.filter(event_type='whatsapp_click').count()
            ph = p_events.filter(event_type='phone_click').count()
            property_breakdown.append({
                'id': str(p.id),
                'title': p.title,
                'status': p.status,
                'views': p.view_count,
                'whatsapp_clicks': wa,
                'phone_clicks': ph,
                'leads': wa + ph,
            })

        return Response({
            'total_properties': total_properties,
            'total_views': total_views,
            'total_inquiries': total_inquiries,
            'total_whatsapp_clicks': total_whatsapp_clicks,
            'total_phone_clicks': total_phone_clicks,
            'daily_trends': daily_trends,
            'property_breakdown': property_breakdown,
        })


class StateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing states.
    """
    queryset = State.objects.all()
    serializer_class = StateSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class LGAViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing LGAs.
    """
    queryset = LGA.objects.all()
    serializer_class = LGASerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    filterset_fields = ['state']


class SavedSearchViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoints for user saved search alerts:
    GET /api/v1/properties/saved-searches/
    POST /api/v1/properties/saved-searches/
    DELETE /api/v1/properties/saved-searches/<id>/
    """
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

