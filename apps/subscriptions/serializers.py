"""
Serializers for subscription plans and user subscriptions.
"""
from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for available subscription plans."""
    
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'price_monthly', 'max_listings', 'boosts_per_month', 'features', 'order']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for a user's active subscription."""
    plan = SubscriptionPlanSerializer(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan', 'status', 'current_period_start', 
            'current_period_end', 'cancel_at_period_end', 'is_valid'
        ]
