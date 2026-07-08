import uuid
from django.conf import settings
from django.db import models


class DeveloperProfile(models.Model):
    """
    Profile for a Developer.
    Developers build housing units, estates, and do bulk/off-plan sales.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='developer_profile',
    )
    company_name = models.CharField(max_length=200, blank=True, default='')
    company_location = models.CharField(
        max_length=300,
        blank=True,
        default='',
        help_text='Physical office/company address.'
    )
    phone_number = models.CharField(max_length=20, blank=True, default='')
    whatsapp_link = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='WhatsApp link (https://wa.me/2348012345678) or phone number.'
    )
    bio = models.TextField(blank=True, default='')
    portfolio_url = models.URLField(
        max_length=300,
        blank=True,
        default='',
        help_text='Link to external website or portfolio.'
    )
    profile_picture = models.ImageField(
        upload_to='developers/profiles/',
        blank=True,
        null=True,
    )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'developer_profiles'
        verbose_name = 'Developer Profile'
        verbose_name_plural = 'Developer Profiles'

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name} ({self.company_name or "Developer"})'

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


class DeveloperReview(models.Model):
    """
    Review and rating submitted by a buyer/client for a developer.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    developer = models.ForeignKey(
        DeveloperProfile,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='developer_reviews',
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text='Rating from 1 to 5 stars',
    )
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'developer_reviews'
        unique_together = ['developer', 'reviewer']
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.rating}★ for {self.developer.company_name or self.developer.user.email} by {self.reviewer.email}'
