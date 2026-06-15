"""
Subscription models for realtors (Pro, Premium, Pro Plus).
"""
import uuid
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """
    Available subscription plans.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, help_text="e.g. Pro, Premium, Pro Plus")
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly price in Naira")
    max_listings = models.PositiveIntegerField(help_text="Maximum allowed active listings")
    boosts_per_month = models.PositiveIntegerField(default=0, help_text="Number of listing boosts per month")
    features = models.JSONField(default=list, help_text="List of feature strings for display")
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0, help_text="Ordering for display")

    class Meta:
        db_table = 'subscription_plans'
        ordering = ['order', 'price_monthly']

    def __str__(self):
        return f"{self.name} (₦{self.price_monthly:,.2f})"


class UserSubscription(models.Model):
    """
    Active subscription for a user (Realtor).
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CANCELED = 'canceled', 'Canceled'
        EXPIRED = 'expired', 'Expired'
        PAST_DUE = 'past_due', 'Past Due'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription',
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscribers',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    
    paystack_subscription_code = models.CharField(max_length=100, blank=True, default='')
    paystack_email_token = models.CharField(max_length=100, blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_subscriptions'

    def __str__(self):
        return f"{self.user.full_name} - {self.plan.name} ({self.status})"

    def is_valid(self):
        return self.status == self.Status.ACTIVE and self.current_period_end > timezone.now()

    def save(self, *args, **kwargs):
        if not self.current_period_end:
            # Default to 30 days if not set
            self.current_period_end = self.current_period_start + timedelta(days=30)
        super().save(*args, **kwargs)
