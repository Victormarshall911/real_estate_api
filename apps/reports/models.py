"""
Crime & Platform Offense Reporting Models.
Allows authenticated users to report real estate crimes, financial scams,
forged documents, fake agents, and extortion with evidence upload.
"""
import uuid
from django.conf import settings
from django.db import models


class CrimeReport(models.Model):
    class Category(models.TextChoices):
        ADVANCE_FEE_FRAUD = 'advance_fee_fraud', 'Advance Fee / Demanded Direct Offline Payment'
        FAKE_AGENT = 'fake_agent', 'Fake Agent / Impersonation'
        FORGED_DOCUMENTS = 'forged_documents', 'Fake or Forged Title Documents'
        LAND_GRABBING_EXTORTION = 'land_grabbing_extortion', 'Land Grabbers (Omo Onile) / Extortion & Threats'
        DUPLICATE_FAKE_LISTING = 'duplicate_fake_listing', 'Duplicate / Stolen Photos / Fake Listing'
        BREACH_OF_ESCROW = 'breach_of_escrow', 'Breach of Escrow / Contract Default'
        CYBERCRIME_PHISHING = 'cybercrime_phishing', 'Cybercrime / Account Takeover / Phishing'
        INSPECTION_SAFETY = 'inspection_safety_incident', 'Physical Danger / Inspection Safety Incident'
        OTHER = 'other_crime', 'Other Crime or Platform Offense'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Compliance Audit'
        UNDER_INVESTIGATION = 'under_investigation', 'Under Active Investigation'
        ESCALATED_AUTHORITIES = 'escalated_to_authorities', 'Escalated to Law Enforcement (Police / EFCC)'
        ACTION_TAKEN = 'action_taken', 'Action Taken (Account/Listing Suspended)'
        RESOLVED = 'resolved', 'Resolved'
        DISMISSED = 'dismissed', 'Dismissed / Inconclusive'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Strictly authenticated reporter
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='crime_reports',
        help_text='Authenticated user filing the crime report.'
    )
    category = models.CharField(
        max_length=40,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True
    )
    title = models.CharField(
        max_length=255,
        help_text='Brief summary headline of the crime or offense.'
    )
    description = models.TextField(
        help_text='Detailed chronological narrative of the crime or offense.'
    )

    # Suspect information
    suspect_name = models.CharField(max_length=200, blank=True, default='', help_text='Suspect individual or company name.')
    suspect_phone = models.CharField(max_length=50, blank=True, default='', help_text='Phone or WhatsApp number used by suspect.')
    suspect_bank_account = models.CharField(max_length=200, blank=True, default='', help_text='Bank name and account number if money was requested.')

    # Associated entities (optional)
    property_listing = models.ForeignKey(
        'properties.PropertyListing',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crime_reports',
        help_text='Property listing involved if applicable.'
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_received',
        help_text='User or agent account reported if on platform.'
    )

    financial_loss = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text='Estimated financial loss incurred in Naira (₦).'
    )
    incident_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date the offense occurred.'
    )
    incident_location = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='City, LGA, state, or address where offense took place.'
    )

    # Evidence uploads
    evidence_file = models.FileField(
        upload_to='crime_reports/evidence/',
        null=True,
        blank=True,
        help_text='Screenshot, chat export, payment receipt, or forged document.'
    )
    evidence_file_2 = models.FileField(
        upload_to='crime_reports/evidence/',
        null=True,
        blank=True,
        help_text='Secondary supporting evidence file.'
    )

    # Resolution & Investigation metadata
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    police_report_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Police SCID or EFCC petition reference tracking ID.'
    )
    admin_notes = models.TextField(
        blank=True,
        default='',
        help_text='Internal notes made by Trust & Safety compliance officers.'
    )
    resolution_summary = models.TextField(
        blank=True,
        default='',
        help_text='Public or reporter-facing resolution explanation.'
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'reports'
        db_table = 'crime_reports'
        verbose_name = 'Crime & Offense Report'
        verbose_name_plural = 'Crime & Offense Reports'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_category_display()}] {self.title} (by {self.reporter.email})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Auto-moderation threshold:
        # If a property receives 3+ pending or active crime reports, automatically flag as is_under_review
        if self.property_listing:
            active_reports = CrimeReport.objects.filter(
                property_listing=self.property_listing,
                status__in=[self.Status.PENDING, self.Status.UNDER_INVESTIGATION, self.Status.ESCALATED_AUTHORITIES]
            ).count()
            if active_reports >= 3 and not self.property_listing.is_under_review:
                self.property_listing.is_under_review = True
                self.property_listing.save(update_fields=['is_under_review'])
