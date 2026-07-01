"""
Architect models for profiles and reviews.
"""
import uuid
from django.conf import settings
from django.db import models


class ArchitectProfile(models.Model):
    """
    Profile for an Architect.
    Architects offer design, building planning, and consultation services.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='architect_profile',
    )
    company_name = models.CharField(max_length=200, blank=True, default='')
    specialization = models.CharField(
        max_length=100,
        blank=True,
        default='Residential & Commercial',
        help_text='e.g., Residential, Commercial, Interior Design, Urban Planning'
    )
    years_of_experience = models.PositiveIntegerField(default=1)
    bio = models.TextField(blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, default='')
    whatsapp_link = models.URLField(max_length=200, blank=True, default='')
    portfolio_url = models.URLField(max_length=300, blank=True, default='', help_text='Link to external design portfolio or website.')
    profile_picture = models.ImageField(
        upload_to='architects/profiles/',
        null=True, blank=True,
    )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'architect_profiles'
        verbose_name = 'Architect Profile'
        verbose_name_plural = 'Architect Profiles'

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name} ({self.company_name})'


class ArchitectReview(models.Model):
    """
    Review and rating submitted by a buyer/client for an architect.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    architect = models.ForeignKey(
        ArchitectProfile,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='architect_reviews',
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text='Rating from 1 to 5 stars',
    )
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'architect_reviews'
        unique_together = ['architect', 'reviewer']
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.rating}★ for {self.architect.company_name} by {self.reviewer.email}'
