import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Wallet(models.Model):
    """
    Virtual wallet for users to hold funds (e.g. for connection fees or escrow).
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
        return f"{self.user.email} - Balance: {self.balance}"


class WalletTransaction(models.Model):
    """
    Records any credit or debit to a wallet.
    """
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),           # Adding money to wallet via payment gateway
        ('withdrawal', 'Withdrawal'),     # Cashing out to bank account
        ('payment', 'Payment'),           # Paying for a service (e.g. escrow/connection fee)
        ('refund', 'Refund'),             # Refunding an escrow or payment
        ('receipt', 'Receipt'),           # Receiving money from an escrow/connection
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wallet_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount} ({self.wallet.user.email})"
