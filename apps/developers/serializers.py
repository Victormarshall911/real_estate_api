from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.utils import get_clean_media_url
from .models import DeveloperProfile, DeveloperReview

User = get_user_model()


class DeveloperReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.first_name', read_only=True)

    class Meta:
        model = DeveloperReview
        fields = ['id', 'reviewer_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer_name', 'created_at']


class DeveloperUserSerializer(serializers.ModelSerializer):
    profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_email_verified', 'profile_photo']
        read_only_fields = fields

    def get_profile_photo(self, obj):
        return get_clean_media_url(obj.profile_photo, self.context.get('request'))


class DeveloperProfileSerializer(serializers.ModelSerializer):
    user = DeveloperUserSerializer(read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    formatted_whatsapp_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = DeveloperProfile
        fields = [
            'id', 'user', 'company_name', 'company_location', 'phone_number',
            'whatsapp_link', 'bio', 'portfolio_url', 'profile_picture',
            'profile_picture_url', 'formatted_whatsapp_url',
            'is_verified', 'created_at', 'updated_at', 'average_rating', 'total_reviews',
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'updated_at']

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
