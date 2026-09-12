import uuid
from django.conf import settings
from django.db import models
from properties.models import PropertyListing


class EscrowTransaction(models.Model):
    """
    Escrow transactions for purchasing properties (buildings or land).
    Supports multi-milestone validation, dual confirmation, and automated dispute mediation.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),        # Proposed by buyer, waiting for seller to accept
        ('escrowed', 'Funds Locked'),           # Accepted by seller, buyer funds are debited & locked in escrow
        ('in_mediation', 'In Mediation'),       # Discrepancy or confirmation conflict, platform team intervened
        ('completed', 'Completed'),             # Both parties confirmed or mediation resolved, funds released to seller
        ('cancelled', 'Cancelled/Refunded'),     # Disputed or rejected, funds returned to buyer
        ('disputed', 'Disputed'),               # Legacy dispute flag
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    
    # Milestone verification flags
    is_inspected = models.BooleanField(default=False)
    is_documents_verified = models.BooleanField(default=False)
    buyer_approved = models.BooleanField(default=False)
    seller_approved = models.BooleanField(default=False)

    # Dual-confirmation tracking
    buyer_confirmed = models.BooleanField(default=False)
    buyer_confirmed_at = models.DateTimeField(null=True, blank=True)
    seller_confirmed = models.BooleanField(default=False)
    seller_confirmed_at = models.DateTimeField(null=True, blank=True)

    # Mediation & Team Involvement
    in_mediation = models.BooleanField(default=False, db_index=True)
    mediation_reason = models.TextField(blank=True, default='', help_text="Reason mediation was triggered")
    mediation_opened_at = models.DateTimeField(null=True, blank=True)
    mediation_resolved_at = models.DateTimeField(null=True, blank=True)
    mediation_resolution_notes = models.TextField(blank=True, default='')
    mediation_status = models.CharField(
        max_length=30,
        default='none',
        choices=(
            ('none', 'No Mediation'),
            ('opened', 'Mediation Case Opened'),
            ('under_review', 'Team Reviewing'),
            ('resolved', 'Mediation Resolved'),
        )
    )
    
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


class EscrowMediation(models.Model):
    """
    Formal dispute/mediation case opened when there is confirmation conflict
    between buyer and seller, or when an issue is reported.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escrow = models.ForeignKey(
        EscrowTransaction,
        on_delete=models.CASCADE,
        related_name='mediations'
    )
    case_number = models.CharField(max_length=50, unique=True, db_index=True)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='initiated_mediations'
    )
    reason = models.TextField()
    evidence_notes = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        default='opened',
        choices=(
            ('opened', 'Opened'),
            ('in_review', 'Under Investigation'),
            ('resolved', 'Resolved'),
            ('dismissed', 'Dismissed'),
        )
    )
    resolution = models.CharField(
        max_length=30,
        blank=True,
        default='',
        choices=(
            ('refund_buyer', 'Refund Buyer In Full'),
            ('release_seller', 'Disburse Funds to Seller'),
            ('split', 'Partial Split / Settlement'),
            ('mutual_agreement', 'Resolved by Mutual Agreement'),
        )
    )
    resolution_notes = models.TextField(blank=True, default='')
    assigned_team = models.CharField(max_length=100, default='LandMarket Trust & Compliance Team')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'escrow_mediations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Mediation Case #{self.case_number} ({self.status})"
