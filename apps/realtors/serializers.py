"""
Serializers for Realtor Profile CRUD and display.
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.utils import get_clean_media_url
from .models import RealtorProfile, RealtorReview

User = get_user_model()


class RealtorReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = RealtorReview
        fields = ['id', 'user_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'user_name', 'created_at']


class RealtorUserSerializer(serializers.ModelSerializer):
    profile_photo = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)
    verification_level = serializers.SerializerMethodField()
    badge_label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'is_email_verified', 'is_kyc_verified', 'is_fully_verified',
            'verification_level', 'badge_label', 'profile_photo',
        ]
        read_only_fields = fields

    def get_profile_photo(self, obj):
        return get_clean_media_url(obj.profile_photo, self.context.get('request'))

    def get_verification_level(self, obj):
        if hasattr(obj, 'kyc_verification'):
            kyc = obj.kyc_verification
            if kyc.status == 'verified':
                return 'cac_verified' if kyc.verification_type == 'cac_certificate' else 'id_verified'
        if obj.is_kyc_verified:
            return 'id_verified'
        if obj.is_email_verified:
            return 'contact_verified'
        return 'unverified'

    def get_badge_label(self, obj):
        level = self.get_verification_level(obj)
        mapping = {
            'cac_verified': 'CAC Registered Agency',
            'id_verified': 'Government ID Verified',
            'contact_verified': 'Contact Verified',
            'unverified': 'Unverified',
        }
        return mapping.get(level, 'Unverified')


class RealtorProfileSerializer(serializers.ModelSerializer):
    user = RealtorUserSerializer(read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    formatted_whatsapp_url = serializers.CharField(read_only=True)
    listing_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()

    class Meta:
        model = RealtorProfile
        fields = [
            'id', 'user', 'company_name', 'phone_number', 'whatsapp_link',
            'bio', 'is_verified', 'profile_picture', 'profile_picture_url',
            'formatted_whatsapp_url', 'total_views', 'listing_count',
            'created_at', 'updated_at', 'average_rating', 'total_reviews',
        ]
        read_only_fields = ['id', 'user', 'total_views', 'created_at', 'updated_at', 'average_rating', 'total_reviews']

    def get_is_verified(self, obj):
        return bool(obj.is_verified or getattr(obj.user, 'is_kyc_verified', False))

    def get_listing_count(self, obj):
        return obj.properties.filter(status='available').count()

    def get_profile_picture_url(self, obj):
        return get_clean_media_url(obj.profile_picture, self.context.get('request'))

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return 0.0
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    def get_total_reviews(self, obj):
        return obj.reviews.count()


class RealtorProfileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealtorProfile
        fields = [
            'id', 'company_name', 'company_location', 'phone_number', 'whatsapp_link',
            'bio', 'profile_picture',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
