from rest_framework import serializers
from .models import EscrowTransaction, EscrowMediation


class EscrowMediationSerializer(serializers.ModelSerializer):
    initiated_by_name = serializers.CharField(source='initiated_by.full_name', read_only=True)
    initiated_by_email = serializers.EmailField(source='initiated_by.email', read_only=True)

    class Meta:
        model = EscrowMediation
        fields = [
            'id', 'case_number', 'initiated_by', 'initiated_by_name',
            'initiated_by_email', 'reason', 'evidence_notes', 'status',
            'resolution', 'resolution_notes', 'assigned_team', 'created_at',
            'resolved_at',
        ]
        read_only_fields = fields


class EscrowTransactionSerializer(serializers.ModelSerializer):
    buyer_email = serializers.EmailField(source='buyer.email', read_only=True)
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    seller_email = serializers.EmailField(source='seller.email', read_only=True)
    seller_name = serializers.CharField(source='seller.full_name', read_only=True)
    property_title = serializers.CharField(source='property_listing.title', read_only=True)
    property_primary_image = serializers.SerializerMethodField()
    mediations = EscrowMediationSerializer(many=True, read_only=True)
    current_user_role = serializers.SerializerMethodField()
    can_confirm = serializers.SerializerMethodField()
    can_reject = serializers.SerializerMethodField()

    class Meta:
        model = EscrowTransaction
        fields = [
            'id', 'buyer', 'buyer_email', 'buyer_name',
            'seller', 'seller_email', 'seller_name',
            'property_listing', 'property_title', 'property_primary_image',
            'amount', 'status', 'is_inspected', 'is_documents_verified',
            'buyer_approved', 'seller_approved',
            'buyer_confirmed', 'buyer_confirmed_at',
            'seller_confirmed', 'seller_confirmed_at',
            'in_mediation', 'mediation_reason', 'mediation_opened_at',
            'mediation_resolved_at', 'mediation_resolution_notes', 'mediation_status',
            'terms', 'dispute_reason', 'mediations',
            'current_user_role', 'can_confirm', 'can_reject',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'buyer', 'seller', 'status', 'is_inspected',
            'is_documents_verified', 'buyer_approved', 'seller_approved',
            'buyer_confirmed', 'buyer_confirmed_at',
            'seller_confirmed', 'seller_confirmed_at',
            'in_mediation', 'mediation_opened_at', 'mediation_resolved_at',
            'mediation_status', 'dispute_reason', 'created_at', 'updated_at'
        ]

    def get_property_primary_image(self, obj):
        request = self.context.get('request')
        if obj.property_listing.primary_image_url:
            from accounts.utils import get_clean_media_url
            return get_clean_media_url(obj.property_listing.primary_image_url, request)
        return None

    def get_current_user_role(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or not user.is_authenticated:
            return None
        if user == obj.buyer:
            return 'buyer'
        if user == obj.seller:
            return 'seller'
        return 'observer'

    def get_can_confirm(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or not user.is_authenticated:
            return False
        if obj.status not in ['escrowed', 'in_mediation']:
            return False
        if user == obj.buyer and not obj.buyer_confirmed:
            return True
        if user == obj.seller and not obj.seller_confirmed:
            return True
        return False

    def get_can_reject(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or not user.is_authenticated:
            return False
        if obj.status == 'escrowed':
            return user in [obj.buyer, obj.seller]
        return False


class EscrowCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscrowTransaction
        fields = ['property_listing', 'amount', 'terms']

    def validate(self, attrs):
        property_listing = attrs.get('property_listing')
        
        # Check listing status
        if property_listing.status != 'available':
            raise serializers.ValidationError({"property_listing": "This property is not currently available for purchase."})

        # Resolve seller
        seller_user = None
        if property_listing.realtor:
            seller_user = property_listing.realtor.user
        elif property_listing.landlord:
            seller_user = property_listing.landlord.user
        elif property_listing.developer:
            seller_user = property_listing.developer.user
        elif property_listing.architect:
            seller_user = property_listing.architect.user
            
        if not seller_user:
            raise serializers.ValidationError({"property_listing": "Could not identify the seller profile associated with this listing."})
            
        attrs['seller'] = seller_user
        return attrs
