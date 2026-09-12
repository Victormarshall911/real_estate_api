from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from wallets.models import Wallet, WalletTransaction

User = get_user_model()


class WalletOperationsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='walletuser@example.com',
            password='testpassword123',
            first_name='Victor',
            last_name='Marshall',
            role='buyer'
        )
        self.wallet = Wallet.objects.get_or_create(user=self.user)[0]
        self.wallet.balance = Decimal('100000.00')
        self.wallet.save()

    def test_get_virtual_account(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('wallet-virtual-account')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('account_number', response.data)
        self.assertIn('bank_name', response.data)
        self.assertEqual(len(response.data['account_number']), 10)

    def test_get_nigerian_banks_list(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('wallet-banks')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 5)
        codes = [b['code'] for b in response.data]
        self.assertIn('058', codes)  # GTBank
        self.assertIn('033', codes)  # UBA

    def test_successful_bank_withdrawal(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('wallet-withdraw')
        payload = {
            'amount': '25000.00',
            'bank_name': 'Guaranty Trust Bank (GTBank)',
            'account_number': '0123456789',
            'account_name': 'Victor Marshall'
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('75000.00'))

        tx = WalletTransaction.objects.filter(wallet=self.wallet, transaction_type='withdrawal').first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, Decimal('25000.00'))
        self.assertEqual(tx.bank_name, 'Guaranty Trust Bank (GTBank)')

    def test_insufficient_funds_withdrawal_fails(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('wallet-withdraw')
        payload = {
            'amount': '500000.00',  # Exceeds 100k balance
            'bank_name': 'Access Bank',
            'account_number': '0123456789',
            'account_name': 'Victor Marshall'
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('100000.00'))
