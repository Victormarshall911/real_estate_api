"""Admin configuration for the properties app."""
from django.contrib import admin
from .models import PropertyListing, PropertyImage, PropertyView, PropertyDocument, VerificationRequest, PropertyAnalyticsEvent, SavedSearch


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    readonly_fields = ('id', 'uploaded_at')


@admin.register(PropertyListing)
class PropertyListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'land_size', 'location', 'status', 'view_count', 'created_at')
    list_filter = ('status', 'state', 'created_at')
    search_fields = ('title', 'description', 'location', 'state')
    readonly_fields = ('id', 'view_count', 'search_vector', 'created_at', 'updated_at')
    raw_id_fields = ('realtor',)
    inlines = [PropertyImageInline]
    list_per_page = 25


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'caption', 'is_primary', 'uploaded_at')
    list_filter = ('is_primary',)
    raw_id_fields = ('property_listing',)


@admin.register(PropertyView)
class PropertyViewAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'viewer_ip', 'viewed_at')
    list_filter = ('viewed_at',)
    readonly_fields = ('id', 'property_listing', 'viewer_ip', 'user_agent', 'viewed_at')
    list_per_page = 50


@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'document_type', 'is_verified', 'uploaded_at')
    list_filter = ('document_type', 'is_verified')
    raw_id_fields = ('property_listing',)


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'requester', 'status', 'fee_charged', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('property_listing__title', 'requester__email', 'report_notes')
    readonly_fields = ('id', 'fee_charged', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status == VerificationRequest.Status.APPROVED:
            obj.property_listing.is_title_verified = True
            obj.property_listing.save(update_fields=['is_title_verified'])
            obj.property_listing.documents.all().update(is_verified=True)
        elif obj.status in [VerificationRequest.Status.REJECTED, VerificationRequest.Status.PENDING]:
            obj.property_listing.is_title_verified = False
            obj.property_listing.save(update_fields=['is_title_verified'])


@admin.register(PropertyAnalyticsEvent)
class PropertyAnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'event_type', 'viewer', 'created_at')
    list_filter = ('event_type', 'created_at')
    raw_id_fields = ('property_listing', 'viewer')


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'state', 'lga', 'max_price', 'email_alerts_enabled', 'created_at')
    list_filter = ('email_alerts_enabled', 'created_at')
    search_fields = ('title', 'user__email')
    raw_id_fields = ('user',)


