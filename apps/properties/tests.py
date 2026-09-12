from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from properties.models import PropertyListing, PropertyReport
from realtors.models import RealtorProfile

User = get_user_model()


class PropertyTrustAndSafetyTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller2@example.com',
            password='testpassword123',
            first_name='Agent',
            last_name='Ade',
            role='realtor'
        )
        self.reporter = User.objects.create_user(
            email='reporter@example.com',
            password='testpassword123',
            first_name='John',
            last_name='Doe',
            role='buyer'
        )
        self.realtor_profile, _ = RealtorProfile.objects.get_or_create(
            user=self.seller,
            defaults={'company_name': 'Ade Properties'}
        )
        self.property = PropertyListing.objects.create(
            realtor=self.realtor_profile,
            title='Suspicious Plot, Ibeju Lekki',
            description='Cheap land with unverified document claims',
            price=Decimal('1500000.00'),
            state='Lagos',
            location='Ibeju Lekki',
            property_category='land',
            land_size=Decimal('500.00'),
            status='active'
        )

    def test_report_listing_creates_property_report(self):
        self.client.force_authenticate(user=self.reporter)
        url = reverse('properties:property-report', kwargs={'pk': self.property.id})
        payload = {
            'reason': 'fake_agent',
            'description': 'Survey plan number does not exist in state surveyor general records.',
            'contact_email': 'reporter@example.com'
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        report = PropertyReport.objects.filter(property_listing=self.property).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reason, 'fake_agent')

    def test_auto_moderation_threshold_flags_property_review(self):
        # Create 3 reports to test the threshold
        for i in range(3):
            u = User.objects.create_user(
                email=f'user{i}@example.com',
                password='testpassword123'
            )
            self.client.force_authenticate(user=u)
            url = reverse('properties:property-report', kwargs={'pk': self.property.id})
            self.client.post(url, {'reason': 'suspicious_payment', 'description': 'Demanded cash payment outside escrow'})

        self.property.refresh_from_db()
        self.assertTrue(self.property.is_under_review)
