from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from escrows.models import EscrowTransaction, EscrowMediation
from properties.models import PropertyListing
from realtors.models import RealtorProfile
from wallets.models import Wallet

User = get_user_model()


class EscrowDualConfirmationTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            password='testpassword123',
            first_name='Buyer',
            last_name='User',
            role='buyer'
        )
        self.seller = User.objects.create_user(
            email='seller@example.com',
            password='testpassword123',
            first_name='Seller',
            last_name='User',
            role='realtor'
        )
        self.buyer_wallet = Wallet.objects.get_or_create(user=self.buyer)[0]
        self.buyer_wallet.balance = Decimal('10000000.00')
        self.buyer_wallet.save()

        self.seller_wallet = Wallet.objects.get_or_create(user=self.seller)[0]
        self.seller_wallet.balance = Decimal('0.00')
        self.seller_wallet.save()

        self.realtor_profile, _ = RealtorProfile.objects.get_or_create(
            user=self.seller,
            defaults={'company_name': 'Premier Estates'}
        )

        self.property = PropertyListing.objects.create(
            realtor=self.realtor_profile,
            title='Prime Waterfront Plot, Lekki Phase 1',
            description='Prime residential plot with C of O',
            price=Decimal('5000000.00'),
            state='Lagos',
            location='Lekki Phase 1',
            property_category='land',
            land_size=Decimal('600.00'),
            status='active'
        )

        self.escrow = EscrowTransaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            property_listing=self.property,
            amount=Decimal('5000000.00'),
            status='pending'
        )

    def test_seller_accepts_escrow_locks_funds(self):
        self.client.force_authenticate(user=self.seller)
        url = reverse('escrow-accept', kwargs={'pk': self.escrow.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.escrow.refresh_from_db()
        self.assertEqual(self.escrow.status, 'escrowed')

        self.buyer_wallet.refresh_from_db()
        self.assertEqual(self.buyer_wallet.balance, Decimal('5000000.00'))

    def test_dual_confirmation_releases_funds_when_both_confirm(self):
        # Move escrow to escrowed state
        self.escrow.status = 'escrowed'
        self.escrow.save()

        # Buyer confirms
        self.client.force_authenticate(user=self.buyer)
        confirm_url = reverse('escrow-confirm', kwargs={'pk': self.escrow.id})
        res1 = self.client.post(confirm_url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        self.escrow.refresh_from_db()
        self.assertTrue(self.escrow.buyer_confirmed)
        self.assertFalse(self.escrow.seller_confirmed)
        self.assertEqual(self.escrow.status, 'escrowed')  # Still waiting for seller

        # Seller confirms
        self.client.force_authenticate(user=self.seller)
        res2 = self.client.post(confirm_url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        self.escrow.refresh_from_db()
        self.assertTrue(self.escrow.buyer_confirmed)
        self.assertTrue(self.escrow.seller_confirmed)
        self.assertEqual(self.escrow.status, 'completed')

        # Seller wallet received funds
        self.seller_wallet.refresh_from_db()
        self.assertEqual(self.seller_wallet.balance, Decimal('5000000.00'))

    def test_discrepancy_rejection_opens_automatic_mediation(self):
        # Move escrow to escrowed state
        self.escrow.status = 'escrowed'
        self.escrow.save()

        # Buyer confirms
        self.client.force_authenticate(user=self.buyer)
        confirm_url = reverse('escrow-confirm', kwargs={'pk': self.escrow.id})
        self.client.post(confirm_url)

        # Seller rejects / reports discrepancy
        self.client.force_authenticate(user=self.seller)
        reject_url = reverse('escrow-reject-confirmation', kwargs={'pk': self.escrow.id})
        res = self.client.post(reject_url, {
            'reason': 'Deed of Assignment signature discrepancy noted upon inspection.'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.escrow.refresh_from_db()
        self.assertEqual(self.escrow.status, 'in_mediation')
        self.assertTrue(self.escrow.in_mediation)

        # Mediation record created
        mediation = EscrowMediation.objects.filter(escrow=self.escrow).first()
        self.assertIsNotNone(mediation)
        self.assertEqual(mediation.status, 'opened')
        self.assertIn('signature discrepancy', mediation.reason)
