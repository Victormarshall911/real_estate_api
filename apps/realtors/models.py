"""
Realtor Profile model with WhatsApp link validation and Cloudinary profile picture.
"""
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def validate_whatsapp_link(value):
    """
    Validates that the value is a proper WhatsApp link or phone number.
    Accepts formats:
      - https://wa.me/2348012345678
      - +2348012345678
      - 2348012345678
    """
    patterns = [
        r'^https?://wa\.me/\d{10,15}$',
        r'^\+?\d{10,15}$',
        r'^https?://api\.whatsapp\.com/send\?phone=\d{10,15}',
    ]
    if not any(re.match(p, value) for p in patterns):
        raise ValidationError(
            'Enter a valid WhatsApp link (https://wa.me/XXXXXXXXXXX) '
            'or phone number (+XXXXXXXXXXX).'
        )


class RealtorProfile(models.Model):
    """
    Extended profile for users with the 'realtor' role.
    One-to-one relationship with CustomUser.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='realtor_profile',
    )
    company_name = models.CharField(max_length=200, blank=True, default='')
    phone_number = models.CharField(max_length=20)
    whatsapp_link = models.CharField(
        max_length=100,
        validators=[validate_whatsapp_link],
        help_text='WhatsApp link (https://wa.me/2348012345678) or phone number.',
    )
    bio = models.TextField(blank=True, default='')
    company_location = models.CharField(
        max_length=300,
        blank=True,
        default='',
        help_text='Physical office/company location.',
    )
    is_verified = models.BooleanField(
        default=False,
        help_text='Verified realtors get a badge on their listings.',
    )
    profile_picture = models.ImageField(
        upload_to='realtors/profile_pictures/',
        blank=True,
        null=True,
        help_text='Uploaded to Cloudinary CDN automatically.',
    )
    total_views = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'realtor_profiles'
        verbose_name = 'Realtor Profile'
        verbose_name_plural = 'Realtor Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.full_name} — {self.company_name or "Independent"}'

    @property
    def profile_picture_url(self):
        """Return the Cloudinary URL or None."""
        if self.profile_picture:
            return self.profile_picture.url
        return None

    @property
    def formatted_whatsapp_url(self):
        """Always return a clickable WhatsApp URL."""
        if self.whatsapp_link.startswith('http'):
            return self.whatsapp_link
        phone = self.whatsapp_link.lstrip('+')
        return f'https://wa.me/{phone}'


class RealtorReview(models.Model):
    """
    Review and rating for a realtor left by a buyer after a transaction.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    realtor = models.ForeignKey(
        RealtorProfile,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='realtor_reviews_left'
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        help_text='Rating from 1 to 5'
    )
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'realtor_reviews'
        ordering = ['-created_at']
        unique_together = ('realtor', 'user')

    def __str__(self):
        return f'{self.rating} Stars for {self.realtor.user.email} by {self.user.email if self.user else "Deleted User"}'

