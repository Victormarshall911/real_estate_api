from django.contrib import admin
from .models import (
    PropertyListing,
    PropertyImage,
    PropertyView,
    PropertyDocument,
    VerificationRequest,
    PropertyReport,
    PropertyAnalyticsEvent,
    SavedSearch,
    State,
    LGA,
)


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(LGA)
class LGAAdmin(admin.ModelAdmin):
    list_display = ('name', 'state')
    list_filter = ('state',)
    search_fields = ('name',)


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


class PropertyDocumentInline(admin.TabularInline):
    model = PropertyDocument
    extra = 1


@admin.register(PropertyListing)
class PropertyListingAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'price', 'property_category', 'property_type',
        'location', 'state', 'status', 'is_title_verified',
        'is_featured', 'is_under_review', 'created_at'
    )
    list_filter = (
        'status', 'property_category', 'property_type',
        'is_title_verified', 'is_featured', 'is_under_review', 'state'
    )
    search_fields = ('title', 'location', 'description')
    inlines = [PropertyImageInline, PropertyDocumentInline]
    actions = ['mark_title_verified', 'mark_under_review', 'clear_under_review']

    def mark_title_verified(self, request, queryset):
        queryset.update(is_title_verified=True)
        self.message_user(request, "Selected properties marked as title verified.")
    mark_title_verified.short_description = "Mark Title Verified"

    def mark_under_review(self, request, queryset):
        queryset.update(is_under_review=True)
        self.message_user(request, "Selected properties flagged as Under Review.")
    mark_under_review.short_description = "Flag as Under Review"

    def clear_under_review(self, request, queryset):
        queryset.update(is_under_review=False)
        self.message_user(request, "Selected properties cleared from Under Review.")
    clear_under_review.short_description = "Clear Under Review Flag"


@admin.register(PropertyReport)
class PropertyReportAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'reason', 'status', 'reporter', 'contact_email', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('property_listing__title', 'description', 'contact_email', 'reporter__email')
    actions = ['mark_resolved', 'mark_under_investigation']

    def mark_resolved(self, request, queryset):
        queryset.update(status=PropertyReport.Status.RESOLVED)
        self.message_user(request, "Selected fraud reports marked as resolved.")
    mark_resolved.short_description = "Mark Selected Reports as Resolved"

    def mark_under_investigation(self, request, queryset):
        queryset.update(status=PropertyReport.Status.UNDER_REVIEW)
        self.message_user(request, "Selected fraud reports marked under investigation.")
    mark_under_investigation.short_description = "Mark Under Investigation"


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'caption', 'is_primary', 'uploaded_at')
    list_filter = ('is_primary',)
    raw_id_fields = ('property_listing',)


@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'document_type', 'is_verified', 'uploaded_at')
    list_filter = ('document_type', 'is_verified')
    raw_id_fields = ('property_listing',)
    actions = ['approve_documents']

    def approve_documents(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f"{count} property documents verified.")
    approve_documents.short_description = "Approve and verify documents"


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'requester', 'status', 'fee_charged', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('property_listing__title', 'requester__email', 'report_notes')
    readonly_fields = ('id', 'fee_charged', 'created_at', 'updated_at')
    actions = ['approve_verification_requests']

    def save_model(self, request, obj, form, change):
        if obj.status == VerificationRequest.Status.APPROVED:
            obj.property_listing.is_title_verified = True
            obj.property_listing.save(update_fields=['is_title_verified'])
        super().save_model(request, obj, form, change)

    def approve_verification_requests(self, request, queryset):
        for req in queryset:
            req.status = VerificationRequest.Status.APPROVED
            req.save(update_fields=['status'])
            req.property_listing.is_title_verified = True
            req.property_listing.save(update_fields=['is_title_verified'])
        self.message_user(request, f"{queryset.count()} title search verification requests approved and badges awarded.")
    approve_verification_requests.short_description = "Approve and award Title Verified Badge"
