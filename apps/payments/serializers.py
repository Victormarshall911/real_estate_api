"""
Serializers for Paystack payment flows.
"""
from rest_framework import serializers
from .models import PaystackPayment


class InitiatePaymentSerializer(serializers.Serializer):
    """Serializer for initiating a Paystack payment."""
    payment_type = serializers.ChoiceField(choices=PaystackPayment.PaymentType.choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class PaymentSerializer(serializers.ModelSerializer):
    """Read-only serializer for payment records."""

    class Meta:
        model = PaystackPayment
        fields = [
            'id', 'payment_type', 'amount', 'reference', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields
