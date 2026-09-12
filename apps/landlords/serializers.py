from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.utils import get_clean_media_url
from .models import LandlordProfile, LandlordReview

User = get_user_model()


class LandlordReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.first_name', read_only=True)

    class Meta:
        model = LandlordReview
        fields = ['id', 'reviewer_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer_name', 'created_at']


class LandlordUserSerializer(serializers.ModelSerializer):
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
                return 'id_verified'
        if obj.is_kyc_verified:
            return 'id_verified'
        if obj.is_email_verified:
            return 'contact_verified'
        return 'unverified'

    def get_badge_label(self, obj):
        return 'Verified Landlord' if self.get_verification_level(obj) == 'id_verified' else 'Unverified'


class LandlordProfileSerializer(serializers.ModelSerializer):
    user = LandlordUserSerializer(read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    formatted_whatsapp_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()

    class Meta:
        model = LandlordProfile
        fields = [
            'id', 'user', 'phone_number', 'whatsapp_link', 'bio',
            'profile_picture', 'profile_picture_url', 'formatted_whatsapp_url',
            'is_verified', 'created_at', 'updated_at', 'average_rating', 'total_reviews',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_verified(self, obj):
        return bool(obj.is_verified or getattr(obj.user, 'is_kyc_verified', False))

    def get_profile_picture_url(self, obj):
        return get_clean_media_url(obj.profile_picture, self.context.get('request'))

    def get_formatted_whatsapp_url(self, obj):
        return obj.formatted_whatsapp_url

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return 0
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    def get_total_reviews(self, obj):
        return obj.reviews.count()
