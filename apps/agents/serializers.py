"""
Serializers for Agent profiles, pricing, and connections.
"""
from rest_framework import serializers
from .models import AgentProfile, AgentLocationPricing, AgentConnection, AgentReview
from accounts.serializers import UserSerializer

class AgentReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = AgentReview
        fields = ['id', 'user_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'user_name', 'created_at']


class AgentLocationPricingSerializer(serializers.ModelSerializer):
    """Serializer for agent per-location pricing."""
    
    class Meta:
        model = AgentLocationPricing
        fields = ['id', 'state', 'location', 'connection_fee', 'is_active']


class AgentProfileSerializer(serializers.ModelSerializer):
    """Serializer for public agent profile display."""
    user = UserSerializer(read_only=True)
    location_prices = AgentLocationPricingSerializer(many=True, read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = AgentProfile
        fields = [
            'id', 'user', 'company_name', 'company_location', 'bio',
            'phone_number', 'whatsapp_link', 'profile_picture_url',
            'is_verified', 'total_connections', 'location_prices', 'created_at',
            'average_rating', 'total_reviews',
        ]

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return 0.0
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    def get_total_reviews(self, obj):
        return obj.reviews.count()


class AgentProfileCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating an agent profile."""
    
    class Meta:
        model = AgentProfile
        fields = [
            'id', 'company_name', 'company_location', 'bio',
            'phone_number', 'whatsapp_link', 'profile_picture',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        
        # Ensure user is marked as agent
        if request.user.role != 'agent':
            request.user.role = 'agent'
            request.user.save(update_fields=['role'])
            
        return super().create(validated_data)


class AgentConnectionSerializer(serializers.ModelSerializer):
    """Serializer for an active connection between a user and an agent."""
    agent = AgentProfileSerializer(read_only=True)
    location_pricing = AgentLocationPricingSerializer(read_only=True)

    class Meta:
        model = AgentConnection
        fields = ['id', 'agent', 'location_pricing', 'status', 'created_at', 'expires_at']
        read_only_fields = fields
