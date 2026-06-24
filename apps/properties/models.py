"""
Property Listing, Property Image, and Property View models.
Includes full-text search indexing via PostgreSQL.
"""
import uuid

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models

from realtors.models import RealtorProfile




class PropertyListing(models.Model):
    """
    A land property listing created by a verified realtor.
    Supports full-text search via PostgreSQL SearchVector.
    """

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        SOLD = 'sold', 'Sold'

    class ListingType(models.TextChoices):
        REGULAR = 'regular', 'Regular'
        UPCOMING = 'upcoming', 'Upcoming Estate'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    realtor = models.ForeignKey(
        RealtorProfile,
        on_delete=models.CASCADE,
        related_name='properties',
    )
    title = models.CharField(max_length=300, db_index=True)
    description = models.TextField(
        help_text='Supports markdown formatting for rich property descriptions.'
    )
    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text='Price in Nigerian Naira (₦).',
    )
    land_size = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Size in square meters.',
    )
    location = models.CharField(
        max_length=300,
        help_text='Human-readable location string (e.g., "Lekki Phase 1, Lagos").',
        db_index=True,
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='State (e.g., "Lagos", "Abuja").',
        db_index=True,
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='GPS latitude for map placement.',
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='GPS longitude for map placement.',
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
    )
    listing_type = models.CharField(
        max_length=15,
        choices=ListingType.choices,
        default=ListingType.REGULAR,
        db_index=True,
    )
    is_featured = models.BooleanField(
        default=False,
        help_text='If true, property appears in the featured carousel.',
        db_index=True,
    )
    video = models.FileField(
        upload_to='properties/videos/',
        null=True,
        blank=True,
        help_text='Optional promotional video for the property.'
    )
    view_count = models.PositiveIntegerField(default=0, editable=False)
    search_vector = SearchVectorField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'property_listings'
        verbose_name = 'Property Listing'
        verbose_name_plural = 'Property Listings'
        ordering = ['-created_at']
        indexes = [
            GinIndex(fields=['search_vector'], name='property_search_idx'),
            models.Index(fields=['price'], name='property_price_idx'),
            models.Index(fields=['land_size'], name='property_size_idx'),
            models.Index(fields=['-created_at', 'status'], name='property_date_status_idx'),
        ]

    def __str__(self):
        return f'{self.title} — ₦{self.price:,.2f}'

    @property
    def land_size_plots(self):
        """Convert square meters to plots (1 plot ≈ 648 sqm in Nigeria)."""
        if self.land_size:
            return round(float(self.land_size) / 648, 2)
        return 0

    @property
    def primary_image_url(self):
        """Return URL of the primary image, or the first image."""
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.image.url if primary.image else None
        first = self.images.first()
        return first.image.url if first and first.image else None


class PropertyImage(models.Model):
    """
    Individual image attached to a property listing.
    Images are stored on Cloudinary CDN via django-cloudinary-storage.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property_listing = models.ForeignKey(
        PropertyListing,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(
        upload_to='properties/images/',
        help_text='Uploaded to Cloudinary CDN automatically.',
    )
    caption = models.CharField(max_length=200, blank=True, default='')
    is_primary = models.BooleanField(
        default=False,
        help_text='The primary image is used as the listing thumbnail.',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'property_images'
        verbose_name = 'Property Image'
        verbose_name_plural = 'Property Images'
        ordering = ['-is_primary', 'uploaded_at']

    def __str__(self):
        return f'Image for {self.property_listing.title} ({"Primary" if self.is_primary else "Secondary"})'


class PropertyView(models.Model):
    """
    Tracks individual views/visits to a property listing for analytics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property_listing = models.ForeignKey(
        PropertyListing,
        on_delete=models.CASCADE,
        related_name='views',
    )
    viewer_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'property_views'
        verbose_name = 'Property View'
        verbose_name_plural = 'Property Views'
        ordering = ['-viewed_at']

    def __str__(self):
        return f'View on {self.property_listing.title} at {self.viewed_at}'
