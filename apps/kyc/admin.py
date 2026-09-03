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

    def _get_secure_url(self, obj):
        if not obj.document_image:
            return None
        url = obj.document_image.url
        # If running on Render behind HTTPS proxy, ensure https scheme
        if url.startswith('http://') and not url.startswith('http://localhost'):
            url = url.replace('http://', 'https://', 1)
        return url

    def document_preview(self, obj):
        if not obj.document_image:
            if obj.status == KYCVerification.Status.VERIFIED:
                return format_html('<span style="color: #059669; font-weight: bold; font-size: 11px;">✅ Verified (Doc deleted for privacy)</span>')
            return format_html('<span style="color: #94a3b8; font-size: 11px;">No document file</span>')

        file_url = self._get_secure_url(obj)
        is_pdf = file_url.lower().endswith('.pdf')

        if is_pdf:
            return format_html(
                '<a href="{}" target="_blank" style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; background: #e0e7ff; color: #3730a3; border-radius: 6px; font-weight: 600; text-decoration: none; font-size: 11px;">'
                '📄 Open PDF ↗'
                '</a>',
                file_url
            )

        return format_html(
            '<div style="display: flex; align-items: center; gap: 6px;">'
            '<a href="{}" target="_blank">'
            '<img src="{}" alt="Doc" style="max-height: 40px; max-width: 70px; object-fit: cover; border-radius: 6px; border: 1px solid #cbd5e1;" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'inline\';" />'
            '<span style="display: none; padding: 3px 6px; background: #f1f5f9; color: #475569; border-radius: 4px; font-size: 10px; font-weight: bold;">📎 File</span>'
            '</a>'
            '<a href="{}" target="_blank" style="font-size: 11px; color: #2563eb; font-weight: bold; text-decoration: underline;">View ↗</a>'
            '</div>',
            file_url, file_url, file_url
        )
    document_preview.short_description = 'Document'

    def document_preview_large(self, obj):
        if not obj.document_image:
            if obj.status == KYCVerification.Status.VERIFIED:
                return format_html(
                    '<div style="padding: 14px; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; color: #065f46; font-size: 13px;">'
                    '✅ <strong>User Identity Verified.</strong> The uploaded document file was automatically deleted upon approval for NDPR / GDPR privacy protection.'
                    '</div>'
                )
            return 'No document uploaded.'

        file_url = self._get_secure_url(obj)
        is_pdf = file_url.lower().endswith('.pdf')

        if is_pdf:
            return format_html(
                '<div style="padding: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;">'
                '<p style="margin-bottom: 8px; font-weight: bold; color: #1e293b;">Uploaded PDF Document:</p>'
                '<a href="{}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #2563eb; color: #fff; border-radius: 6px; font-weight: bold; text-decoration: none;">'
                '📄 Open / Inspect Full PDF Document ↗'
                '</a>'
                '</div>',
                file_url
            )

        return format_html(
            '<div style="padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;">'
            '<a href="{}" target="_blank">'
            '<img src="{}" alt="KYC Document Preview" style="max-height: 450px; max-width: 100%; border-radius: 8px; border: 1px solid #cbd5e1;" />'
            '</a>'
            '<p style="margin-top: 10px;">'
            '<a href="{}" target="_blank" style="display: inline-block; padding: 6px 14px; background: #2563eb; color: #fff; border-radius: 6px; font-weight: bold; text-decoration: none; font-size: 12px;">'
            'Open Original Document in New Tab ↗'
            '</a>'
            '</p>'
            '</div>',
            file_url, file_url, file_url
        )
    document_preview_large.short_description = 'Document Preview'

    def save_model(self, request, obj, form, change):
        """Single-item save in admin: Auto-deletes file on verification approval."""
        if obj.status == KYCVerification.Status.VERIFIED:
            if not obj.verified_at:
                obj.verified_at = timezone.now()
            # Delete uploaded file immediately upon approval for user privacy
            if obj.document_image:
                try:
                    obj.document_image.delete(save=False)
                except Exception:
                    pass
                obj.document_image = None

            # Sync verified status to user role profiles
            user = obj.user
            for profile_attr in ['realtor', 'developer', 'landlord', 'agent', 'architect']:
                profile = getattr(user, profile_attr, None)
                if profile and hasattr(profile, 'is_verified'):
                    profile.is_verified = True
                    profile.save(update_fields=['is_verified'])

        super().save_model(request, obj, form, change)

    def approve_verifications(self, request, queryset):
        """Bulk action: Approves KYC and automatically deletes sensitive document files for privacy."""
        count = 0
        now = timezone.now()
        for verification in queryset:
            verification.status = KYCVerification.Status.VERIFIED
            verification.verified_at = now

            # Delete the document file to protect user privacy
            if verification.document_image:
                try:
                    verification.document_image.delete(save=False)
                except Exception:
                    pass
                verification.document_image = None

            verification.save(update_fields=['status', 'verified_at', 'document_image'])

            # Sync verified status to associated user profile roles
            user = verification.user
            for profile_attr in ['realtor', 'developer', 'landlord', 'agent', 'architect']:
                profile = getattr(user, profile_attr, None)
                if profile and hasattr(profile, 'is_verified'):
                    profile.is_verified = True
                    profile.save(update_fields=['is_verified'])
            count += 1

        self.message_user(
            request,
            f'Successfully approved and verified {count} KYC submissions. Original document files were automatically and securely deleted for user privacy.'
        )
    approve_verifications.short_description = 'Approve selected KYC submissions (Awards Verified Badge & Deletes Document)'

    def reject_verifications(self, request, queryset):
        count = queryset.update(status=KYCVerification.Status.FAILED)
        self.message_user(request, f'Marked {count} KYC submissions as rejected.')
    reject_verifications.short_description = 'Reject selected KYC submissions'
