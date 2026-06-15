"""
Views for KYC verification: initiate, check status, and Dojah webhook.
"""
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import KYCVerification
from .serializers import InitiateKYCSerializer, KYCStatusSerializer
from .services import DojahService


class InitiateKYCView(APIView):
    """
    POST /api/v1/kyc/initiate/
    Starts a KYC verification for the authenticated user.
    Calls Dojah API and records the result.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Check if user already has a verified KYC
        existing = KYCVerification.objects.filter(
            user=request.user, status='verified'
        ).first()
        if existing:
            return Response(
                {'message': 'You are already KYC verified.', 'status': 'verified'},
                status=status.HTTP_200_OK,
            )

        serializer = InitiateKYCSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vtype = serializer.validated_data['verification_type']
        id_number = serializer.validated_data['id_number']

        # Call Dojah
        service = DojahService()
        customer_ref = str(request.user.id)

        if vtype == 'bvn':
            result = service.verify_bvn(id_number, customer_ref)
        elif vtype == 'nin':
            result = service.verify_nin(id_number, customer_ref)
        else:
            return Response(
                {'error': f'Verification type "{vtype}" is not yet supported.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete any previous failed/pending attempts
        KYCVerification.objects.filter(
            user=request.user, status__in=['pending', 'failed']
        ).delete()

        # Determine status
        kyc_status = 'verified' if result['success'] else 'failed'

        verification = KYCVerification.objects.create(
            user=request.user,
            verification_type=vtype,
            id_number=id_number,
            reference_id=customer_ref,
            status=kyc_status,
            response_data=result.get('data', {}),
            verified_at=timezone.now() if kyc_status == 'verified' else None,
        )

        # Update user's KYC flag
        if kyc_status == 'verified':
            request.user.is_kyc_verified = True
            request.user.save(update_fields=['is_kyc_verified'])

        return Response(
            {
                'status': kyc_status,
                'message': (
                    'Identity verified successfully!'
                    if kyc_status == 'verified'
                    else result.get('error', 'Verification failed. Please try again.')
                ),
                'verification': KYCStatusSerializer(verification).data,
            },
            status=status.HTTP_200_OK if kyc_status == 'verified' else status.HTTP_400_BAD_REQUEST,
        )


class KYCStatusView(APIView):
    """
    GET /api/v1/kyc/status/
    Returns the authenticated user's KYC verification status.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            verification = KYCVerification.objects.get(user=request.user)
            return Response(KYCStatusSerializer(verification).data)
        except KYCVerification.DoesNotExist:
            return Response(
                {'status': 'none', 'message': 'No KYC verification on file.'},
                status=status.HTTP_200_OK,
            )


class DojahWebhookView(APIView):
    """
    POST /api/v1/kyc/webhook/
    Receives async verification results from Dojah.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # In production, verify webhook signature here
        reference = request.data.get('customer_reference', '')
        event_status = request.data.get('status', '')

        if reference and event_status:
            try:
                verification = KYCVerification.objects.get(reference_id=reference)
                if event_status == 'successful':
                    verification.status = 'verified'
                    verification.verified_at = timezone.now()
                    verification.response_data = request.data
                    verification.save(update_fields=['status', 'verified_at', 'response_data'])

                    verification.user.is_kyc_verified = True
                    verification.user.save(update_fields=['is_kyc_verified'])
                elif event_status == 'failed':
                    verification.status = 'failed'
                    verification.response_data = request.data
                    verification.save(update_fields=['status', 'response_data'])
            except KYCVerification.DoesNotExist:
                pass

        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
