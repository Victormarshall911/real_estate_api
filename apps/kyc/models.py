"""
KYC Verification model — tracks identity and corporate verification via ID document and CAC certificate uploads.
"""
import uuid
from django.conf import settings
from django.db import models


class KYCVerification(models.Model):
    """
    Records an identity or corporate verification submission for a user.
    Supports Driver's License, International Passport, Voter's Card, and CAC Business Certificate.
    """

    class VerificationType(models.TextChoices):
        DRIVERS_LICENSE = 'drivers_license', "Driver's License"
        INTERNATIONAL_PASSPORT = 'international_passport', "International Passport"
        VOTERS_CARD = 'voters_card', "Voter's Card"
        CAC_CERTIFICATE = 'cac_certificate', "CAC Registration Certificate"
        NATIONAL_ID = 'national_id', "National ID Card/Slip"

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        VERIFIED = 'verified', 'Verified'
        FAILED = 'failed', 'Rejected'
        EXPIRED = 'expired', 'Expired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kyc_verification',
    )
    provider = models.CharField(max_length=50, default='document_upload')
    verification_type = models.CharField(
        max_length=30,
        choices=VerificationType.choices,
        default=VerificationType.DRIVERS_LICENSE,
    )
    document_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='ID card number or CAC Registration / BN number.',
    )
    id_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Legacy ID reference if applicable.',
    )
    document_image = models.FileField(
        upload_to='kyc_documents/',
        null=True,
        blank=True,
        help_text='Uploaded photo of the ID card or CAC certificate.',
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Internal or third-party verification reference.',
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(
        blank=True,
        default='',
        help_text='Reason for rejection if verification failed.',
    )
    response_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Metadata or review notes.',
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'kyc_verifications'
        verbose_name = 'KYC Verification'
        verbose_name_plural = 'KYC Verifications'
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.user.email} — {self.get_verification_type_display()} ({self.status})'

    @property
    def verification_level(self):
        if self.status != self.Status.VERIFIED:
            return 'unverified'
        if self.verification_type == self.VerificationType.CAC_CERTIFICATE:
            return 'cac_verified'
        return 'id_verified'
