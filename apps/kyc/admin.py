"""Admin configuration for the KYC verification app."""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import KYCVerification


@admin.register(KYCVerification)
class KYCVerificationAdmin(admin.ModelAdmin):
    list_display = (
        'user_email',
        'verification_type',
        'document_number',
        'document_preview',
        'status',
        'submitted_at',
        'verified_at',
    )
    list_filter = ('status', 'verification_type', 'submitted_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'document_number')
    readonly_fields = ('id', 'document_preview_large', 'submitted_at', 'verified_at')
    actions = ['approve_verifications', 'reject_verifications']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    def document_preview(self, obj):
        if obj.document_image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-height: 40px; border-radius: 6px;" /></a>',
                obj.document_image.url,
                obj.document_image.url
            )
        return '—'
    document_preview.short_description = 'Document'

    def document_preview_large(self, obj):
        if obj.document_image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-height: 400px; border-radius: 8px; border: 1px solid #ddd;" /></a>',
                obj.document_image.url,
                obj.document_image.url
            )
        return 'No document uploaded.'
    document_preview_large.short_description = 'Document Preview'

    def approve_verifications(self, request, queryset):
        count = 0
        now = timezone.now()
        for verification in queryset:
            verification.status = KYCVerification.Status.VERIFIED
            verification.verified_at = now
            verification.save(update_fields=['status', 'verified_at'])
            
            # Sync verified status to associated user profile roles
            user = verification.user
            for profile_attr in ['realtor', 'developer', 'landlord', 'agent', 'architect']:
                profile = getattr(user, profile_attr, None)
                if profile and hasattr(profile, 'is_verified'):
                    profile.is_verified = True
                    profile.save(update_fields=['is_verified'])
            count += 1
        self.message_user(request, f'Successfully approved and verified {count} KYC submissions.')
    approve_verifications.short_description = 'Approve selected KYC submissions (Awards Verified Badge)'

    def reject_verifications(self, request, queryset):
        count = queryset.update(status=KYCVerification.Status.FAILED)
        self.message_user(request, f'Marked {count} KYC submissions as rejected.')
    reject_verifications.short_description = 'Reject selected KYC submissions'
