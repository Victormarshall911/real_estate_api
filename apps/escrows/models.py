import uuid
from django.conf import settings
from django.db import models
from properties.models import PropertyListing


class EscrowTransaction(models.Model):
    """
    Escrow transactions for purchasing properties (buildings or land).
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),    # Proposed by buyer, waiting for seller to accept
        ('escrowed', 'Funds Locked'),       # Accepted by seller, buyer funds are debited & locked in escrow
        ('completed', 'Completed'),         # Inspection/documents validated, funds released to seller
        ('cancelled', 'Cancelled/Refunded'), # Disputed or rejected, funds returned to buyer
        ('disputed', 'Disputed'),           # Flagged for admin arbitration
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='escrow_purchases'
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='escrow_sales'
    )
    property_listing = models.ForeignKey(
        PropertyListing,
        on_delete=models.CASCADE,
        related_name='escrows'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Milestone verification flags
    is_inspected = models.BooleanField(default=False)
    is_documents_verified = models.BooleanField(default=False)
    buyer_approved = models.BooleanField(default=False)
    seller_approved = models.BooleanField(default=False)
    
    # Notes/messages
    terms = models.TextField(blank=True, default='', help_text="Proposed terms, duration, or specifications")
    dispute_reason = models.TextField(blank=True, default='', help_text="Reason for raising a dispute")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'escrow_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Escrow {self.id} - {self.property_listing.title} ({self.status})"
