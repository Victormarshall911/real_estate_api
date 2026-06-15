"""
Agent models for profiles, pricing per location, and user-agent connections.
"""
import uuid

from django.conf import settings
from django.db import models

from payments.models import PaystackPayment


class AgentProfile(models.Model):
    """
    Profile for an Agent. 
    Agents are intermediaries who help buyers and sellers for a fixed connection fee.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_profile',
    )
    company_name = models.CharField(max_length=200, blank=True, default='')
    company_location = models.CharField(max_length=300, blank=True, default='')
    bio = models.TextField(blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, default='')
    whatsapp_link = models.URLField(max_length=200, blank=True, default='')
    profile_picture = models.ImageField(
        upload_to='agents/profiles/',
        null=True, blank=True,
    )
    is_verified = models.BooleanField(default=False)
    total_connections = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'agent_profiles'
        verbose_name = 'Agent Profile'
        verbose_name_plural = 'Agent Profiles'

    def __str__(self):
        return f'{self.user.full_name} ({self.company_name})'


class AgentLocationPricing(models.Model):
    """
    Defines the connection fee an agent charges for a specific location.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        AgentProfile,
        on_delete=models.CASCADE,
        related_name='location_prices',
    )
    state = models.CharField(max_length=100)
    location = models.CharField(max_length=200, help_text='City or specific area.')
    connection_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Fee in Naira (₦) required to unlock contact and chat.',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'agent_location_pricing'
        unique_together = ('agent', 'state', 'location')

    def __str__(self):
        return f'{self.location}, {self.state} — ₦{self.connection_fee:,.2f}'


class AgentConnection(models.Model):
    """
    Records a paid connection between a user (buyer/seller) and an agent.
    Grants access to the chat room and agent contact details.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Payment'
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_connections',
    )
    agent = models.ForeignKey(
        AgentProfile,
        on_delete=models.CASCADE,
        related_name='client_connections',
    )
    location_pricing = models.ForeignKey(
        AgentLocationPricing,
        on_delete=models.SET_NULL,
        null=True,
    )
    payment = models.ForeignKey(
        PaystackPayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Optional expiration date for the connection.',
    )

    class Meta:
        db_table = 'agent_connections'
        unique_together = ('user', 'agent')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.full_name} ↔ {self.agent.user.full_name} ({self.status})'
