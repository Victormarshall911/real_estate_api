"""
Serializers for Architect Profile CRUD and display.
"""
from django.contrib.auth import get_user_model
from django.db.models import Avg
from rest_framework import serializers

from accounts.utils import get_clean_media_url
from .models import ArchitectProfile, ArchitectReview

User = get_user_model()


class ArchitectReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.first_name', read_only=True)

    class Meta:
        model = ArchitectReview
        fields = ['id', 'reviewer_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer_name', 'created_at']


class ArchitectUserSerializer(serializers.ModelSerializer):
    """Lightweight user data nested inside architect serializer."""
    profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_email_verified', 'profile_photo']
        read_only_fields = fields

    def get_profile_photo(self, obj):
        return get_clean_media_url(obj.profile_photo, self.context.get('request'))


class ArchitectProfileSerializer(serializers.ModelSerializer):
    """Full architect profile serializer with nested user and computed fields."""
    user = ArchitectUserSerializer(read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    formatted_whatsapp_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = ArchitectProfile
        fields = [
            'id', 'user', 'company_name', 'specialization', 'years_of_experience',
            'phone_number', 'whatsapp_link', 'portfolio_url', 'bio', 'is_verified',
            'profile_picture', 'profile_picture_url', 'formatted_whatsapp_url',
            'created_at', 'updated_at', 'average_rating', 'total_reviews',
        ]
        read_only_fields = ['id', 'user', 'is_verified', 'created_at', 'updated_at', 'average_rating', 'total_reviews']

    def get_profile_picture_url(self, obj):
        return get_clean_media_url(obj.profile_picture, self.context.get('request'))

    def get_formatted_whatsapp_url(self, obj):
        if obj.whatsapp_link:
            return obj.whatsapp_link
        if obj.phone_number:
            clean_num = ''.join(filter(str.isdigit, obj.phone_number))
            return f'https://wa.me/{clean_num}'
        return ''

    def get_average_rating(self, obj):
        avg = obj.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0.0

    def get_total_reviews(self, obj):
        return obj.reviews.count()
