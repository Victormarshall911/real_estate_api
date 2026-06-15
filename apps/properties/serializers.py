"""
Serializers for Property Listings and Images.
Provides lightweight list serializer and detailed serializer with nested relations.
"""
from rest_framework import serializers

from realtors.serializers import RealtorProfileSerializer
from .models import PropertyListing, PropertyImage


class PropertyImageSerializer(serializers.ModelSerializer):
    """Serializer for individual property images."""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'image_url', 'caption', 'is_primary', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def get_image_url(self, obj):
        """Return the full absolute URL."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class PropertyImageUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to an existing property."""

    class Meta:
        model = PropertyImage
        fields = ['image', 'caption', 'is_primary']


class PropertyListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for property grid/list views.
    Includes primary image and basic realtor info to minimize payload.
    """
    primary_image_url = serializers.SerializerMethodField()
    land_size_plots = serializers.FloatField(read_only=True)
    realtor_name = serializers.SerializerMethodField()
    realtor_id = serializers.UUIDField(source='realtor.id', read_only=True)
    is_verified = serializers.BooleanField(source='realtor.is_verified', read_only=True)
    image_count = serializers.SerializerMethodField()

    class Meta:
        model = PropertyListing
        fields = [
            'id', 'title', 'price', 'land_size', 'land_size_plots',
            'location', 'state', 'status', 'listing_type', 'is_featured', 'primary_image_url',
            'realtor_name', 'realtor_id', 'is_verified', 'image_count',
            'view_count', 'created_at',
        ]
        read_only_fields = fields

    def get_realtor_name(self, obj):
        return obj.realtor.user.full_name

    def get_image_count(self, obj):
        return obj.images.count()

    def get_primary_image_url(self, obj):
        url = obj.primary_image_url
        if url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class PropertyDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for property detail view.
    Includes all images and full realtor profile.
    """
    images = PropertyImageSerializer(many=True, read_only=True)
    realtor = RealtorProfileSerializer(read_only=True)
    land_size_plots = serializers.FloatField(read_only=True)
    primary_image_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyListing
        fields = [
            'id', 'title', 'description', 'price', 'land_size',
            'land_size_plots', 'location', 'state', 'latitude', 'longitude',
            'status', 'listing_type', 'is_featured', 'video', 'primary_image_url', 'images', 'realtor',
            'view_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'view_count', 'created_at', 'updated_at']

    def get_primary_image_url(self, obj):
        url = obj.primary_image_url
        if url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class PropertyCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating property listings.
    Images are uploaded separately via the image upload endpoint.
    """
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text='Upload multiple images with the listing.',
    )

    class Meta:
        model = PropertyListing
        fields = [
            'title', 'description', 'price', 'land_size',
            'location', 'state', 'latitude', 'longitude',
            'status', 'listing_type', 'is_featured', 'video', 'uploaded_images',
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price must be greater than zero.')
        return value

    def validate_land_size(self, value):
        if value <= 0:
            raise serializers.ValidationError('Land size must be greater than zero.')
        return value

    def create(self, validated_data):
        """Create property and attach any uploaded images."""
        uploaded_images = validated_data.pop('uploaded_images', [])
        request = self.context['request']
        validated_data['realtor'] = request.user.realtor_profile

        property_listing = PropertyListing.objects.create(**validated_data)

        # Create image objects for each uploaded file
        for i, image_file in enumerate(uploaded_images):
            PropertyImage.objects.create(
                property_listing=property_listing,
                image=image_file,
                is_primary=(i == 0),  # First image is primary
            )

        return property_listing

    def update(self, instance, validated_data):
        """Update property. Images are managed separately."""
        validated_data.pop('uploaded_images', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
