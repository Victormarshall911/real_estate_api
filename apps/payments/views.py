"""
Paystack payment views: initiation and webhook callback.
"""
import uuid
import hashlib
import hmac

from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PaystackPayment
from .serializers import InitiatePaymentSerializer, PaymentSerializer


class InitiatePaymentView(APIView):
    """
    POST /api/v1/payments/initiate/
    Creates a payment record and returns a Paystack reference.
    In production, this would call Paystack's Initialize Transaction API.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reference = f'LM-{uuid.uuid4().hex[:12].upper()}'

        payment = PaystackPayment.objects.create(
            user=request.user,
            payment_type=serializer.validated_data['payment_type'],
            amount=serializer.validated_data['amount'],
            reference=reference,
            status='pending',
        )

        # In production, call Paystack API here:
        # response = requests.post(
        #     'https://api.paystack.co/transaction/initialize',
        #     headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
        #     json={
        #         'email': request.user.email,
        #         'amount': int(payment.amount * 100),  # Paystack uses kobo
        #         'reference': reference,
        #         'callback_url': f'{settings.FRONTEND_URL}/payment/callback',
        #     }
        # )

        return Response(
            {
                'reference': reference,
                'payment_id': str(payment.id),
                'message': 'Payment initiated. Complete on Paystack.',
                # 'authorization_url': response.json()['data']['authorization_url'],
            },
            status=status.HTTP_201_CREATED,
        )


class PaystackWebhookView(APIView):
    """
    POST /api/v1/payments/webhook/
    Paystack sends payment confirmation webhooks here.
    Verifies the webhook signature and updates payment status.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Verify webhook signature
        paystack_secret = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        signature = request.headers.get('X-Paystack-Signature', '')

        if paystack_secret:
            expected_sig = hmac.new(
                paystack_secret.encode('utf-8'),
                request.body,
                hashlib.sha512,
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_sig):
                return Response(
                    {'error': 'Invalid signature.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Process the webhook event
        event = request.data.get('event', '')
        data = request.data.get('data', {})

        if event == 'charge.success':
            reference = data.get('reference', '')
            try:
                payment = PaystackPayment.objects.get(reference=reference)
                payment.status = 'success'
                payment.paystack_transaction_id = str(data.get('id', ''))
                payment.metadata = data
                payment.save(update_fields=['status', 'paystack_transaction_id', 'metadata', 'updated_at'])
            except PaystackPayment.DoesNotExist:
                pass

        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class PaymentHistoryView(generics.ListAPIView):
    """
    GET /api/v1/payments/history/
    Returns the authenticated user's payment history.
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaystackPayment.objects.filter(user=self.request.user)
