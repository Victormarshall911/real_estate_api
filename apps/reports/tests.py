from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from properties.models import PropertyListing
from reports.models import CrimeReport

User = get_user_model()


class CrimeReportTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='reporter@example.com',
            password='Password123!',
            first_name='Reporter',
            last_name='User'
        )
        self.property = PropertyListing.objects.create(
            title='Suspicious Lekki Land',
            description='Prime land with doubtful survey.',
            price=Decimal('25000000.00'),
            land_size=Decimal('600.00'),
            location='Lekki Phase 1',
            state='Lagos'
        )

    def test_unauthenticated_cannot_submit_crime_report(self):
        url = reverse('crime-report-submit-report')
        payload = {
            'category': 'advance_fee_fraud',
            'title': 'Extortion attempt by fake surveyor',
            'description': 'Demanded direct cash transfer of 500,000 without contract.'
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_submits_crime_report(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('crime-report-submit-report')
        payload = {
            'category': 'forged_documents',
            'title': 'Forged C of O discovered at registry',
            'description': 'Legal search revealed the Certificate of Occupancy presented was forged and registered to someone else.',
            'suspect_name': 'Scammer John',
            'suspect_phone': '08012345678',
            'suspect_bank_account': 'GTBank - 0123456789',
            'financial_loss': '150000.00',
            'property_listing': str(self.property.id)
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CrimeReport.objects.filter(reporter=self.user).count(), 1)
        report = CrimeReport.objects.first()
        self.assertEqual(report.suspect_name, 'Scammer John')
        self.assertEqual(report.financial_loss, Decimal('150000.00'))

    def test_my_reports_endpoint(self):
        self.client.force_authenticate(user=self.user)
        CrimeReport.objects.create(
            reporter=self.user,
            category=CrimeReport.Category.FAKE_AGENT,
            title='Fake agent claiming to represent landlord',
            description='Agent demanded cash payment upfront and vanished.'
        )
        url = reverse('crime-report-my-reports')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Fake agent claiming to represent landlord')

    def test_auto_moderation_3_reports_flags_property_under_review(self):
        self.assertFalse(self.property.is_under_review)
        # Create 3 reports for this property
        for i in range(3):
            u = User.objects.create_user(
                email=f'victim{i}@example.com',
                password='Password123!',
                first_name=f'Victim{i}',
                last_name='Test'
            )
            CrimeReport.objects.create(
                reporter=u,
                category=CrimeReport.Category.DUPLICATE_FAKE_LISTING,
                title=f'Fraud Report #{i+1}',
                description='Multiple people are advertising this exact same land with fake documents.',
                property_listing=self.property
            )

        self.property.refresh_from_db()
        self.assertTrue(self.property.is_under_review)

    def test_categories_endpoint(self):
        url = reverse('crime-report-categories')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 8)
