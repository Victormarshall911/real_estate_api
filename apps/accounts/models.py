"""
Custom User model with email as the primary identifier and role-based access.
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using email instead of username.
    Supports roles: buyer, realtor, agent, and admin.
    """

    class Role(models.TextChoices):
        BUYER = 'buyer', 'Buyer'
        REALTOR = 'realtor', 'Realtor'
        AGENT = 'agent', 'Agent'
        ADMIN = 'admin', 'Admin'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.BUYER,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # ── KYC & Profile Completion ──────────────
    date_of_birth = models.DateField(
        null=True, blank=True,
        help_text='Required for full profile verification.',
    )
    full_address = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Full residential or business address.',
    )
    profile_photo = models.ImageField(
        upload_to='users/profile_photos/',
        null=True, blank=True,
        help_text='Profile photo for identity.',
    )
    is_profile_complete = models.BooleanField(
        default=False,
        help_text='True when the user has filled in all required profile fields.',
    )
    is_kyc_verified = models.BooleanField(
        default=False,
        help_text='True when the user has passed KYC identity verification.',
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.email})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_fully_verified(self):
        """True only when both KYC and profile completion are done."""
        return self.is_kyc_verified and self.is_profile_complete
