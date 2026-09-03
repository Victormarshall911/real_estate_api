"""
Views for KYC verification: document submission and status tracking.
"""
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import KYCVerification
from .serializers import InitiateKYCSerializer, KYCStatusSerializer


class InitiateKYCView(APIView):
    """
    POST /api/v1/kyc/initiate/
    Submits an ID card or CAC certificate document upload for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = InitiateKYCSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vtype = serializer.validated_data.get('verification_type', KYCVerification.VerificationType.DRIVERS_LICENSE)
        doc_number = serializer.validated_data.get('document_number', '').strip()
        doc_image = serializer.validated_data.get('document_image')

        # Update or create verification entry
        verification, created = KYCVerification.objects.update_or_create(
            user=request.user,
            defaults={
                'verification_type': vtype,
                'document_number': doc_number,
                'document_image': doc_image if doc_image else None,
                'status': KYCVerification.Status.PENDING,
                'submitted_at': timezone.now(),
            }
        )

        return Response(
            {
                'status': 'pending',
                'message': 'Your documents have been submitted successfully and are under review by our compliance team.',
                'verification': KYCStatusSerializer(verification).data,
            },
            status=status.HTTP_200_OK,
        )


class KYCStatusView(APIView):
    """
    GET /api/v1/kyc/status/
    Returns current KYC verification status.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            verification = KYCVerification.objects.get(user=request.user)
            return Response(KYCStatusSerializer(verification).data)
        except KYCVerification.DoesNotExist:
            return Response(
                {'status': 'none', 'message': 'No verification on file.'},
                status=status.HTTP_200_OK,
            )
