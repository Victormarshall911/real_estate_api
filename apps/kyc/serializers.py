"""
Serializers for KYC verification.
"""
from rest_framework import serializers
from .models import KYCVerification


class InitiateKYCSerializer(serializers.Serializer):
    """Validates input for starting a KYC verification."""
    verification_type = serializers.ChoiceField(
        choices=KYCVerification.VerificationType.choices,
    )
    id_number = serializers.CharField(max_length=50)

    def validate_id_number(self, value):
        """Basic format validation."""
        cleaned = value.strip().replace('-', '').replace(' ', '')
        if not cleaned.isdigit():
            raise serializers.ValidationError('ID number must contain only digits.')
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise serializers.ValidationError('ID number must be between 10 and 15 digits.')
        return cleaned


class KYCStatusSerializer(serializers.ModelSerializer):
    """Read-only serializer for KYC status."""

    class Meta:
        model = KYCVerification
        fields = [
            'id', 'verification_type', 'status', 'provider',
            'submitted_at', 'verified_at',
        ]
        read_only_fields = fields
