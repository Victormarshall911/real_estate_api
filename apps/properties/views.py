import logging
from django.db import models
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from accounts.permissions import IsOwnerOrReadOnly, CanListProperties
from .filters import PropertyFilter
from .models import (
    PropertyListing,
    PropertyImage,
    PropertyDocument,
    PropertyReport,
    VerificationRequest,
    PropertyAnalyticsEvent,
    SavedSearch,
    State,
    LGA,
)
from .serializers import (
    PropertyListSerializer,
    PropertyDetailSerializer,
    PropertyCreateSerializer,
    PropertyImageSerializer,
    PropertyDocumentSerializer,
    PropertyReportSerializer,
    SavedSearchSerializer,
    StateSerializer,
    LGASerializer,
)

logger = logging.getLogger(__name__)


class PropertyViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, CanListProperties]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PropertyFilter
    ordering_fields = ['price', 'land_size', 'created_at', 'view_count']
    ordering = ['-created_at']
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        if self.action == 'my_listings':
            user = self.request.user
            if not user.is_authenticated:
                return PropertyListing.objects.none()
            return (
                PropertyListing.objects
                .select_related('realtor', 'landlord', 'developer', 'architect', 'state_ref', 'lga_ref')
                .prefetch_related('images', 'documents')
                .filter(
                    models.Q(realtor__user=user) |
                    models.Q(landlord__user=user) |
                    models.Q(developer__user=user) |
                    models.Q(architect__user=user)
                )
            )
        return (
            PropertyListing.objects
            .select_related('realtor', 'landlord', 'developer', 'architect', 'state_ref', 'lga_ref')
            .prefetch_related('images', 'documents')
            .exclude(status=PropertyListing.Status.UNDER_REVIEW)
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return PropertyListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return PropertyCreateSerializer
        return PropertyDetailSerializer

    def perform_create(self, serializer):
        user = self.request.user
        extra_kwargs = {}
        if hasattr(user, 'realtor_profile'):
            extra_kwargs['realtor'] = user.realtor_profile
        elif hasattr(user, 'landlord_profile'):
            extra_kwargs['landlord'] = user.landlord_profile
        elif hasattr(user, 'developer_profile'):
            extra_kwargs['developer'] = user.developer_profile
        elif hasattr(user, 'architect_profile'):
            extra_kwargs['architect'] = user.architect_profile
        serializer.save(**extra_kwargs)

    @action(detail=False, methods=['get'], url_path='my-listings', permission_classes=[permissions.IsAuthenticated])
    def my_listings(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PropertyListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = PropertyListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured_properties = (
            PropertyListing.objects
            .filter(status=PropertyListing.Status.AVAILABLE, is_featured=True)
            .select_related('realtor', 'state_ref', 'lga_ref')
            .prefetch_related('images', 'documents')
            .order_by('-created_at')[:8]
        )
        serializer = PropertyListSerializer(featured_properties, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def report(self, request, pk=None):
        """
        POST /api/v1/properties/<id>/report/
        Community fraud & trust reporting endpoint with auto-moderation.
        """
        property_obj = self.get_object()
        serializer = PropertyReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(
            property_listing=property_obj,
            reporter=request.user if request.user.is_authenticated else None,
        )

        # Auto-moderation thresholds
        pending_reports_count = property_obj.reports.filter(status=PropertyReport.Status.PENDING).count()
        if pending_reports_count >= 5:
            property_obj.status = PropertyListing.Status.UNDER_REVIEW
            property_obj.is_under_review = True
            property_obj.save(update_fields=['status', 'is_under_review'])
        elif pending_reports_count >= 3:
            property_obj.is_under_review = True
            property_obj.save(update_fields=['is_under_review'])

        return Response({
            'message': 'Report submitted successfully. Our trust and safety team will investigate.',
            'report_id': str(report.id),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='images', permission_classes=[permissions.IsAuthenticated])
    def upload_images(self, request, pk=None):
        property_obj = self.get_object()
        files = request.FILES.getlist('images')
        if not files:
            return Response({'error': 'No image files provided.'}, status=status.HTTP_400_BAD_REQUEST)

        created_images = []
        has_primary = property_obj.images.filter(is_primary=True).exists()
        for i, f in enumerate(files):
            img = PropertyImage.objects.create(
                property_listing=property_obj,
                image=f,
                is_primary=(not has_primary and i == 0),
            )
            created_images.append(img)

        serializer = PropertyImageSerializer(created_images, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='upload-document', permission_classes=[permissions.IsAuthenticated])
    def upload_document(self, request, pk=None):
        property_obj = self.get_object()
        file_obj = request.FILES.get('file')
        doc_type = request.data.get('document_type', 'other')

        if not file_obj:
            return Response({'error': 'No document file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        doc = PropertyDocument.objects.create(
            property_listing=property_obj,
            document_type=doc_type,
            file=file_obj,
            is_verified=False
        )

        if doc_type == 'c_of_o':
            property_obj.has_c_of_o = True
        elif doc_type == 'survey_plan':
            property_obj.has_survey_plan = True
        property_obj.save()

        serializer = PropertyDocumentSerializer(doc, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='request-verification', permission_classes=[permissions.IsAuthenticated])
    def request_verification(self, request, pk=None):
        property_obj = self.get_object()
        req = VerificationRequest.objects.create(
            requester=request.user,
            property_listing=property_obj,
            status=VerificationRequest.Status.PENDING,
            fee_charged=10000.00
        )
        return Response({'message': 'Title verification request submitted successfully.', 'request_id': str(req.id)})

    @action(detail=False, methods=['get'], url_path='my-verifications', permission_classes=[permissions.IsAuthenticated])
    def my_verifications(self, request):
        reqs = VerificationRequest.objects.filter(requester=request.user)
        data = [{
            'id': str(r.id),
            'property_id': str(r.property_listing.id),
            'property_title': r.property_listing.title,
            'status': r.status,
            'fee_charged': str(r.fee_charged),
            'created_at': r.created_at,
        } for r in reqs]
        return Response(data)

    @action(detail=True, methods=['post'], url_path='track-event', permission_classes=[permissions.AllowAny])
    def track_event(self, request, pk=None):
        property_obj = self.get_object()
        event_type = request.data.get('event_type', 'view')
        if event_type == 'view':
            PropertyListing.objects.filter(pk=property_obj.pk).update(view_count=models.F('view_count') + 1)

        PropertyAnalyticsEvent.objects.create(
            property_listing=property_obj,
            event_type=event_type,
            viewer=request.user if request.user.is_authenticated else None,
        )
        return Response({'status': 'tracked', 'event_type': event_type}, status=status.HTTP_201_CREATED)


class StateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class LGAViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LGA.objects.select_related('state').all()
    serializer_class = LGASerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        state_id = self.request.query_params.get('state')
        if state_id:
            qs = qs.filter(state_id=state_id)
        return qs


class SavedSearchViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SavedSearchSerializer
    
    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)
