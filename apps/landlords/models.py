import uuid
from django.conf import settings
from django.db import models


class LandlordProfile(models.Model):
    """
    Profile for a Landlord.
    Landlords own land/properties and can lease or sell them.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='landlord_profile',
    )
    phone_number = models.CharField(max_length=20, blank=True, default='')
    whatsapp_link = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='WhatsApp link (https://wa.me/2348012345678) or phone number.'
    )
    bio = models.TextField(blank=True, default='')
    profile_picture = models.ImageField(
        upload_to='landlords/profiles/',
        blank=True,
        null=True,
    )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'landlord_profiles'
        verbose_name = 'Landlord Profile'
        verbose_name_plural = 'Landlord Profiles'

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name} (Landlord)'

    @property
    def profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return None

    @property
    def formatted_whatsapp_url(self):
        if not self.whatsapp_link:
            return ''
        if self.whatsapp_link.startswith('http'):
            return self.whatsapp_link
        phone = self.whatsapp_link.lstrip('+')
        return f'https://wa.me/{phone}'


class LandlordReview(models.Model):
    """
    Review and rating submitted by a buyer/client for a landlord.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    landlord = models.ForeignKey(
        LandlordProfile,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='landlord_reviews',
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text='Rating from 1 to 5 stars',
    )
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'landlord_reviews'
        unique_together = ['landlord', 'reviewer']
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.rating}★ for {self.landlord.user.email} by {self.reviewer.email}'
