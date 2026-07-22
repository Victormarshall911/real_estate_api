"""
Property Listing, Property Image, and Property View models.
Includes full-text search indexing via PostgreSQL.
"""
import uuid

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.conf import settings

from realtors.models import RealtorProfile




class State(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)

    class Meta:
        db_table = 'property_states'
        verbose_name = 'State'
        verbose_name_plural = 'States'
        ordering = ['name']

    def __str__(self):
        return self.name


class LGA(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='lgas')

    class Meta:
        db_table = 'property_lgas'
        verbose_name = 'LGA'
        verbose_name_plural = 'LGAs'
        ordering = ['name']
        unique_together = ('name', 'state')

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class PropertyListing(models.Model):
    """
    A land property listing created by a verified realtor.
    Supports full-text search via PostgreSQL SearchVector.
    """

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        SOLD = 'sold', 'Sold'

    class PropertyCategory(models.TextChoices):
        LAND = 'land', 'Land'
        BUILDING = 'building', 'Building'

    class PropertyType(models.TextChoices):
        PLOT = 'plot', 'Plot'
        ESTATE = 'estate', 'Upcoming Estate'
        HOUSE = 'house', 'House'
        APARTMENT = 'apartment', 'Apartment'
        COMMERCIAL = 'commercial', 'Commercial Space'
        OFFICE = 'office', 'Office Space'
        SHORT_LET = 'short_let_apartment', 'Short-Let Apartment'

    class ListingType(models.TextChoices):
        SALE = 'sale', 'For Sale'
        RENT = 'rent', 'For Rent'
        LEASE = 'lease', 'For Lease'
        SHORT_LET = 'short_let', 'Short-Let'
        REGULAR = 'regular', 'Regular'
        UPCOMING = 'upcoming', 'Upcoming Estate'

    class RentFrequency(models.TextChoices):
        YEARLY = 'yearly', 'Yearly'
        MONTHLY = 'monthly', 'Monthly'
        DAILY = 'daily', 'Daily'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    realtor = models.ForeignKey(
        RealtorProfile,
        on_delete=models.CASCADE,
        related_name='properties',
        null=True,
        blank=True,
    )
    landlord = models.ForeignKey(
        'landlords.LandlordProfile',
        on_delete=models.CASCADE,
        related_name='properties',
        null=True,
        blank=True,
    )
    developer = models.ForeignKey(
        'developers.DeveloperProfile',
        on_delete=models.CASCADE,
        related_name='properties',
        null=True,
        blank=True,
    )
    architect = models.ForeignKey(
        'architects.ArchitectProfile',
        on_delete=models.CASCADE,
        related_name='properties',
        null=True,
        blank=True,
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
    property_category = models.CharField(
        max_length=20,
        choices=PropertyCategory.choices,
        default=PropertyCategory.LAND,
        db_index=True,
    )
    property_type = models.CharField(
        max_length=30,
        choices=PropertyType.choices,
        default=PropertyType.PLOT,
        db_index=True,
    )
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.PositiveIntegerField(null=True, blank=True)
    built_up_area = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Built-up area in square meters (for houses/apartments).'
    )
    # Amenity Flags
    has_electricity = models.BooleanField(default=False)
    has_water = models.BooleanField(default=False)
    has_drainage = models.BooleanField(default=False)
    has_security = models.BooleanField(default=False)
    has_generator = models.BooleanField(default=False)
    has_c_of_o = models.BooleanField(default=False)
    has_survey_plan = models.BooleanField(default=False)

    # Rental details
    rent_frequency = models.CharField(
        max_length=15,
        choices=RentFrequency.choices,
        null=True,
        blank=True,
        db_index=True,
    )
    caution_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    agency_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    legal_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Structured Locations
    state_ref = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        related_name='properties',
        null=True,
        blank=True,
    )
    lga_ref = models.ForeignKey(
        LGA,
        on_delete=models.SET_NULL,
        related_name='properties',
        null=True,
        blank=True,
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
    is_title_verified = models.BooleanField(
        default=False,
        help_text='Indicates if the property title has been verified by the LandMarket legal team.'
    )
    listing_type = models.CharField(
        max_length=15,
        choices=ListingType.choices,
        default=ListingType.SALE,
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


class PropertyDocument(models.Model):
    """
    Legal documents uploaded for a property listing (e.g. C of O, Survey Plan).
    """
    class DocumentType(models.TextChoices):
        C_OF_O = 'c_of_o', 'Certificate of Occupancy'
        DEED = 'deed_of_assignment', 'Deed of Assignment'
        SURVEY = 'survey_plan', 'Registered Survey Plan'
        GAZETTE = 'gazette', 'Excision Gazette'
        OTHER = 'other', 'Other Document'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property_listing = models.ForeignKey(
        PropertyListing,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    file = models.FileField(upload_to='property_documents/')
    is_verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'property_documents'
        verbose_name = 'Property Legal Document'
        verbose_name_plural = 'Property Legal Documents'
        ordering = ['uploaded_at']

    def __str__(self):
        return f'{self.get_document_type_display()} for {self.property_listing.title}'


class VerificationRequest(models.Model):
    """
    A buyer or seller request for LandMarket legal team to verify title documents.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Search'
        IN_PROGRESS = 'in_progress', 'Search In Progress'
        APPROVED = 'approved', 'Approved / Title Clear'
        REJECTED = 'rejected', 'Rejected / Title Disputed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification_requests',
    )
    property_listing = models.ForeignKey(
        PropertyListing,
        on_delete=models.CASCADE,
        related_name='verification_requests',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    report_notes = models.TextField(blank=True, default='')
    fee_charged = models.DecimalField(max_digits=12, decimal_places=2, default=10000.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'property_verification_requests'
        verbose_name = 'Title Verification Request'
        verbose_name_plural = 'Title Verification Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'Search Request by {self.requester.email} on {self.property_listing.title} ({self.get_status_display()})'


class PropertyAnalyticsEvent(models.Model):
    """
    Tracks analytical events like views and lead generation clicks for a property.
    """
    class EventType(models.TextChoices):
        VIEW = 'view', 'Page View'
        WHATSAPP_CLICK = 'whatsapp_click', 'WhatsApp Click'
        PHONE_CLICK = 'phone_click', 'Phone Call Click'
        ESCROW_PROPOSE = 'escrow_propose', 'Escrow Inquiry'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property_listing = models.ForeignKey(
        PropertyListing,
        on_delete=models.CASCADE,
        related_name='analytics_events',
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.VIEW,
        db_index=True,
    )
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='viewed_events',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'property_analytics_events'
        verbose_name = 'Property Analytics Event'
        verbose_name_plural = 'Property Analytics Events'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_event_type_display()} on {self.property_listing.title}'


class SavedSearch(models.Model):
    """
    Stores user filter parameters for saved searches and automatic notification alerts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_searches',
    )
    title = models.CharField(max_length=255, help_text="e.g. Lekki Residential Plots under ₦100M")
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saved_searches',
    )
    lga = models.ForeignKey(
        LGA,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saved_searches',
    )
    property_type = models.CharField(max_length=50, blank=True, null=True)
    max_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    min_bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    email_alerts_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saved_searches'
        verbose_name = 'Saved Search'
        verbose_name_plural = 'Saved Searches'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.user.email})'
