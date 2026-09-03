"""
Serializers for document-based KYC verification.
"""
from rest_framework import serializers
from .models import KYCVerification


class InitiateKYCSerializer(serializers.ModelSerializer):
    """Validates document upload submission for KYC."""
    
    class Meta:
        model = KYCVerification
        fields = ['verification_type', 'document_number', 'document_image']
        extra_kwargs = {
            'document_image': {'required': False},
            'document_number': {'required': False},
        }


class KYCStatusSerializer(serializers.ModelSerializer):
    """Read-only serializer for KYC status."""
    verification_level = serializers.CharField(read_only=True)
    verification_type_display = serializers.CharField(source='get_verification_type_display', read_only=True)

    class Meta:
        model = KYCVerification
        fields = [
            'id', 'verification_type', 'verification_type_display',
            'verification_level', 'status', 'document_number',
            'submitted_at', 'verified_at', 'rejection_reason',
        ]
        read_only_fields = fields
