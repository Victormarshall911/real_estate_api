"""
KYC Verification model — tracks identity verification via Dojah API.
"""
import uuid

from django.conf import settings
from django.db import models


class KYCVerification(models.Model):
    """
    Records a KYC identity verification attempt for a user.
    Uses Dojah (Nigeria-appropriate KYC provider) for BVN/NIN verification.
    """

    class VerificationType(models.TextChoices):
        BVN = 'bvn', 'Bank Verification Number'
        NIN = 'nin', 'National Identification Number'
        DRIVERS_LICENSE = 'drivers_license', "Driver's License"

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        VERIFIED = 'verified', 'Verified'
        FAILED = 'failed', 'Failed'
        EXPIRED = 'expired', 'Expired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kyc_verification',
    )
    provider = models.CharField(max_length=50, default='dojah')
    verification_type = models.CharField(
        max_length=20,
        choices=VerificationType.choices,
    )
    id_number = models.CharField(
        max_length=50,
        help_text='The BVN, NIN, or license number submitted for verification.',
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Dojah transaction reference.',
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    response_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Full response from the KYC provider.',
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'kyc_verifications'
        verbose_name = 'KYC Verification'
        verbose_name_plural = 'KYC Verifications'
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.user.email} — {self.verification_type} ({self.status})'
