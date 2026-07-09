from rest_framework import serializers
from .models import EscrowTransaction


class EscrowTransactionSerializer(serializers.ModelSerializer):
    buyer_email = serializers.EmailField(source='buyer.email', read_only=True)
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    seller_email = serializers.EmailField(source='seller.email', read_only=True)
    seller_name = serializers.CharField(source='seller.full_name', read_only=True)
    property_title = serializers.CharField(source='property_listing.title', read_only=True)
    property_primary_image = serializers.SerializerMethodField()

    class Meta:
        model = EscrowTransaction
        fields = [
            'id', 'buyer', 'buyer_email', 'buyer_name',
            'seller', 'seller_email', 'seller_name',
            'property_listing', 'property_title', 'property_primary_image',
            'amount', 'status', 'is_inspected', 'is_documents_verified',
            'buyer_approved', 'seller_approved', 'terms', 'dispute_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'buyer', 'seller', 'status', 'is_inspected',
            'is_documents_verified', 'buyer_approved', 'seller_approved',
            'dispute_reason', 'created_at', 'updated_at'
        ]

    def get_property_primary_image(self, obj):
        request = self.context.get('request')
        if obj.property_listing.primary_image_url:
            from accounts.utils import get_clean_media_url
            return get_clean_media_url(obj.property_listing.primary_image_url, request)
        return None


class EscrowCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscrowTransaction
        fields = ['property_listing', 'amount', 'terms']

    def validate(self, attrs):
        property_listing = attrs.get('property_listing')
        
        # Check listing status
        if property_listing.status != 'active':
            raise serializers.ValidationError({"property_listing": "This property is not currently active for purchase."})

        # Resolve seller
        seller_user = None
        if property_listing.realtor:
            seller_user = property_listing.realtor.user
        elif property_listing.landlord:
            seller_user = property_listing.landlord.user
        elif property_listing.developer:
            seller_user = property_listing.developer.user
            
        if not seller_user:
            raise serializers.ValidationError({"property_listing": "Could not identify the seller profile associated with this listing."})
            
        attrs['seller'] = seller_user
        return attrs
