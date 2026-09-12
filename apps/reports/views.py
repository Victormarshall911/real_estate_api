"""
Views for Crime & Offense Reporting.
Enforces authentication on report creation and history.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from .models import CrimeReport
from .serializers import (
    CrimeReportCreateSerializer,
    CrimeReportListSerializer,
    CrimeReportDetailSerializer
)


class CrimeReportViewSet(viewsets.GenericViewSet):
    """
    API endpoint for authenticated users to report crimes, fraud, and offenses.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return CrimeReport.objects.all()
        return CrimeReport.objects.filter(reporter=user)

    @action(detail=False, methods=['post'], url_path='submit')
    def submit_report(self, request):
        """Submit a new crime/offense report with optional evidence attachments."""
        serializer = CrimeReportCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        report = serializer.save(reporter=request.user)

        return Response({
            'message': 'Crime report submitted successfully. Our Trust & Safety team and compliance officers have received your report.',
            'report': CrimeReportDetailSerializer(report, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my-reports')
    def my_reports(self, request):
        """List all crime reports filed by the authenticated user."""
        reports = CrimeReport.objects.filter(reporter=request.user)
        serializer = CrimeReportListSerializer(reports, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Retrieve full details and investigation status of a crime report."""
        report = self.get_object()
        serializer = CrimeReportDetailSerializer(report, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def categories(self, request):
        """Returns crime category choices and their user-friendly labels."""
        data = [
            {'key': key, 'label': label}
            for key, label in CrimeReport.Category.choices
        ]
        return Response(data)
