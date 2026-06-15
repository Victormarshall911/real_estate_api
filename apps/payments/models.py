"""
Paystack payment model for realtor listing fees.
Stub implementation — ready for full Paystack integration.
"""
import uuid

from django.conf import settings
from django.db import models


class PaystackPayment(models.Model):
    """
    Records payment transactions for listing fees.
    Uses Paystack (Nigeria-appropriate payment gateway).
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    class PaymentType(models.TextChoices):
        LISTING_FEE = 'listing_fee', 'Listing Fee'
        FEATURED_LISTING = 'featured_listing', 'Featured Listing'
        VERIFICATION_FEE = 'verification_fee', 'Verification Fee'
        AGENT_CONNECTION = 'agent_connection', 'Agent Connection Fee'
        MEETING_FEE = 'meeting_fee', 'Meeting Fee'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.LISTING_FEE,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Amount in Naira (₦).',
    )
    reference = models.CharField(
        max_length=100,
        unique=True,
        help_text='Paystack transaction reference.',
    )
    paystack_access_code = models.CharField(max_length=100, blank=True, default='')
    paystack_transaction_id = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'paystack_payments'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.payment_type} — ₦{self.amount:,.2f} ({self.status})'
