"""
Serializers for Realtor Profile CRUD and display.
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import RealtorProfile

User = get_user_model()


class RealtorUserSerializer(serializers.ModelSerializer):
    """Lightweight user data nested inside realtor serializer."""

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_email_verified']
        read_only_fields = fields


class RealtorProfileSerializer(serializers.ModelSerializer):
    """Full realtor profile serializer with nested user and computed fields."""
    user = RealtorUserSerializer(read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    formatted_whatsapp_url = serializers.CharField(read_only=True)
    listing_count = serializers.SerializerMethodField()

    class Meta:
        model = RealtorProfile
        fields = [
            'id', 'user', 'company_name', 'phone_number', 'whatsapp_link',
            'bio', 'is_verified', 'profile_picture', 'profile_picture_url',
            'formatted_whatsapp_url', 'total_views', 'listing_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'is_verified', 'total_views', 'created_at', 'updated_at']

    def get_listing_count(self, obj):
        """Count of active property listings for this realtor."""
        return obj.properties.filter(status='available').count()

    def get_profile_picture_url(self, obj):
        url = obj.profile_picture_url
        if url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class RealtorProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating a realtor profile."""

    class Meta:
        model = RealtorProfile
        fields = [
            'company_name', 'phone_number', 'whatsapp_link',
            'bio', 'profile_picture',
        ]

    def create(self, validated_data):
        """Link profile to the authenticated user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
