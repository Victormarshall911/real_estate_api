import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Wallet(models.Model):
    """
    Virtual wallet for users to hold funds (e.g. for connection fees, inspection, or escrow).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wallets'

    def __str__(self):
        return f"{self.user.email} - Balance: ₦{self.balance:,.2f}"

    @property
    def locked_in_escrow(self):
        """Calculates total funds currently held in active escrow transactions for this buyer."""
        from escrows.models import EscrowTransaction
        escrows = EscrowTransaction.objects.filter(
            buyer=self.user,
            status__in=['escrowed', 'in_mediation']
        )
        total = sum((e.amount for e in escrows), Decimal('0.00'))
        return total


class WalletTransaction(models.Model):
    """
    Records any credit or debit to a wallet, including bank withdrawals and virtual account deposits.
    """
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),           # Adding money to wallet via payment gateway or bank transfer
        ('withdrawal', 'Withdrawal'),     # Cashing out to Nigerian bank account
        ('payment', 'Payment'),           # Paying for a service (e.g. escrow/connection fee)
        ('refund', 'Refund'),             # Refunding an escrow or payment
        ('receipt', 'Receipt'),           # Receiving money from an escrow payout
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True, help_text="Unique external or internal reference")
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')

    # Bank payout metadata
    bank_name = models.CharField(max_length=100, blank=True, default='')
    account_number = models.CharField(max_length=20, blank=True, default='')
    account_name = models.CharField(max_length=150, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wallet_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - ₦{self.amount:,.2f} ({self.wallet.user.email})"
