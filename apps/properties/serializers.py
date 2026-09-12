"""
Serializers for property listings, images, documents, and community fraud reports.
"""
from rest_framework import serializers

from accounts.utils import get_clean_media_url
from .models import (
    PropertyListing,
    PropertyImage,
    PropertyDocument,
    PropertyReport,
    State,
    LGA,
    SavedSearch,
)
from realtors.serializers import RealtorProfileSerializer
from landlords.serializers import LandlordProfileSerializer
from developers.serializers import DeveloperProfileSerializer
from architects.serializers import ArchitectProfileSerializer


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'name']


class LGASerializer(serializers.ModelSerializer):
    class Meta:
        model = LGA
        fields = ['id', 'name', 'state']


class PropertyImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'image_url', 'caption', 'is_primary', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def get_image_url(self, obj):
        return get_clean_media_url(obj.image, self.context.get('request'))


class PropertyDocumentSerializer(serializers.ModelSerializer):
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyDocument
        fields = ['id', 'document_type', 'document_file', 'document_url', 'is_verified', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'is_verified']

    def get_document_url(self, obj):
        return get_clean_media_url(obj.document_file, self.context.get('request'))


class PropertyListingSerializer(serializers.ModelSerializer):
    primary_image_url = serializers.SerializerMethodField()
    land_size_plots = serializers.FloatField(read_only=True)
    state_name = serializers.SerializerMethodField()
    lga_name = serializers.SerializerMethodField()
    realtor_name = serializers.SerializerMethodField()
    realtor_company = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    seller_role = serializers.SerializerMethodField()
    seller_verified = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = PropertyListing
        fields = [
            'id', 'title', 'price', 'land_size', 'land_size_plots',
            'location', 'state', 'status', 'listing_type', 'is_featured', 'is_under_review',
            'primary_image_url', 'view_count', 'created_at',
            'property_category', 'property_type', 'bedrooms', 'bathrooms',
            'has_c_of_o', 'has_survey_plan', 'rent_frequency',
            'is_title_verified', 'state_name', 'lga_name',
            'realtor_name', 'realtor_company', 'seller_name', 'seller_role',
            'seller_verified', 'is_verified', 'document_count'
        ]

    def get_primary_image_url(self, obj):
        return get_clean_media_url(obj.primary_image_url, self.context.get('request'))

    def get_state_name(self, obj):
        return obj.state_ref.name if obj.state_ref else obj.state

    def get_lga_name(self, obj):
        return obj.lga_ref.name if obj.lga_ref else obj.location

    def get_realtor_name(self, obj):
        return obj.realtor.user.full_name if obj.realtor else None

    def get_realtor_company(self, obj):
        return obj.realtor.company_name if obj.realtor else None

    def get_seller_name(self, obj):
        if obj.realtor:
            return obj.realtor.user.full_name
        if obj.landlord:
            return obj.landlord.user.full_name
        if obj.developer:
            return obj.developer.company_name or obj.developer.user.full_name
        if obj.architect:
            return obj.architect.user.full_name
        return None

    def get_seller_role(self, obj):
        if obj.realtor:
            return 'realtor'
        if obj.developer:
            return 'developer'
        if obj.landlord:
            return 'landlord'
        if obj.architect:
            return 'architect'
        return 'seller'

    def get_seller_verified(self, obj):
        seller = obj.realtor or obj.developer or obj.landlord or obj.architect
        if not seller:
            return False
        return bool(getattr(seller, 'is_verified', False) or (hasattr(seller, 'user') and getattr(seller.user, 'is_kyc_verified', False)))

    def get_is_verified(self, obj):
        return self.get_seller_verified(obj)

    def get_document_count(self, obj):
        return obj.documents.filter(is_verified=True).count()


class PropertyDetailSerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    realtor = RealtorProfileSerializer(read_only=True)
    landlord = LandlordProfileSerializer(read_only=True)
    developer = DeveloperProfileSerializer(read_only=True)
    architect = ArchitectProfileSerializer(read_only=True)
    land_size_plots = serializers.FloatField(read_only=True)
    primary_image_url = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    lga_name = serializers.SerializerMethodField()
    state_ref = StateSerializer(read_only=True)
    lga_ref = LGASerializer(read_only=True)
    documents = serializers.SerializerMethodField()
    investment_metrics = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()

    def get_is_verified(self, obj):
        seller = obj.realtor or obj.developer or obj.landlord or obj.architect
        if not seller:
            return False
        return bool(getattr(seller, 'is_verified', False) or (hasattr(seller, 'user') and getattr(seller.user, 'is_kyc_verified', False)))

    def get_documents(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        is_owner = False
        if user and user.is_authenticated:
            if obj.realtor and obj.realtor.user == user:
                is_owner = True
            elif obj.landlord and obj.landlord.user == user:
                is_owner = True
            elif obj.developer and obj.developer.user == user:
                is_owner = True
            elif obj.architect and obj.architect.user == user:
                is_owner = True
            elif user.is_staff:
                is_owner = True
        
        docs = obj.documents.all()
        if not is_owner:
            return [
                {
                    'id': str(d.id),
                    'document_type': d.document_type,
                    'is_verified': d.is_verified,
                    'uploaded_at': d.uploaded_at
                }
                for d in docs
            ]
        return PropertyDocumentSerializer(docs, many=True, context=self.context).data

    def get_investment_metrics(self, obj):
        return {
            'estimated_roi_pct': 14.5,
            'price_per_sqm': round(float(obj.price) / float(obj.land_size), 2) if obj.land_size and float(obj.land_size) > 0 else 0,
            'location_growth_rate': 'High (18-22% YoY)',
            'rental_yield_estimate': '7.2% / year',
        }

    class Meta:
        model = PropertyListing
        fields = [
            'id', 'realtor', 'landlord', 'developer', 'architect', 'title', 'description', 'price',
            'agency_fee', 'legal_fee', 'caution_fee', 'service_charge', 'total_package_fee',
            'property_category', 'property_type', 'bedrooms', 'bathrooms',
            'has_c_of_o', 'has_survey_plan', 'rent_frequency', 'listing_type',
            'land_size', 'land_size_plots', 'location', 'state', 'state_ref', 'lga_ref',
            'latitude', 'longitude', 'status', 'is_title_verified', 'is_verified', 'is_featured', 'is_under_review',
            'video', 'view_count', 'primary_image_url', 'images', 'documents',
            'investment_metrics', 'state_name', 'lga_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'view_count', 'created_at', 'updated_at']

    def get_primary_image_url(self, obj):
        return get_clean_media_url(obj.primary_image_url, self.context.get('request'))

    def get_state_name(self, obj):
        return obj.state_ref.name if obj.state_ref else obj.state

    def get_lga_name(self, obj):
        return obj.lga_ref.name if obj.lga_ref else obj.location


class PropertyListingCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyListing
        fields = [
            'id', 'title', 'description', 'price',
            'agency_fee', 'legal_fee', 'caution_fee', 'service_charge',
            'property_category', 'property_type', 'bedrooms', 'bathrooms',
            'has_c_of_o', 'has_survey_plan', 'rent_frequency', 'listing_type',
            'land_size', 'location', 'state', 'state_ref', 'lga_ref',
            'latitude', 'longitude', 'status', 'is_featured', 'video',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        user = self.context['request'].user
        if hasattr(user, 'realtor_profile'):
            validated_data['realtor'] = user.realtor_profile
        elif hasattr(user, 'developer_profile'):
            validated_data['developer'] = user.developer_profile
        elif hasattr(user, 'landlord_profile'):
            validated_data['landlord'] = user.landlord_profile
        elif hasattr(user, 'architect_profile'):
            validated_data['architect'] = user.architect_profile
        elif user.role == 'realtor':
            from realtors.models import RealtorProfile
            profile, _ = RealtorProfile.objects.get_or_create(user=user)
            validated_data['realtor'] = profile
        elif user.role == 'developer':
            from developers.models import DeveloperProfile
            profile, _ = DeveloperProfile.objects.get_or_create(user=user)
            validated_data['developer'] = profile
        elif user.role == 'landlord':
            from landlords.models import LandlordProfile
            profile, _ = LandlordProfile.objects.get_or_create(user=user)
            validated_data['landlord'] = profile
        elif user.role == 'architect':
            from architects.models import ArchitectProfile
            profile, _ = ArchitectProfile.objects.get_or_create(user=user)
            validated_data['architect'] = profile

        return super().create(validated_data)


class PropertyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyReport
        fields = ['id', 'reason', 'description', 'contact_email', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']


# Aliases for backward compatibility
PropertyListSerializer = PropertyListingSerializer
PropertyCreateSerializer = PropertyListingCreateUpdateSerializer


class SavedSearchSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='state.name', read_only=True)
    lga_name = serializers.CharField(source='lga.name', read_only=True)

    class Meta:
        model = SavedSearch
        fields = [
            'id', 'title', 'state', 'state_name', 'lga', 'lga_name',
            'property_type', 'max_price', 'min_bedrooms', 'email_alerts_enabled', 'created_at'
        ]
