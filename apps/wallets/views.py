import uuid
from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Wallet, WalletTransaction
from .serializers import (
    WalletSerializer,
    WalletTransactionSerializer,
    DepositSerializer,
    WithdrawalSerializer
)

NIGERIAN_BANKS = [
    {"code": "058", "name": "Guaranty Trust Bank (GTBank)"},
    {"code": "057", "name": "Zenith Bank"},
    {"code": "044", "name": "Access Bank"},
    {"code": "011", "name": "First Bank of Nigeria"},
    {"code": "033", "name": "United Bank for Africa (UBA)"},
    {"code": "035", "name": "Wema Bank / ALAT"},
    {"code": "101", "name": "Providus Bank"},
    {"code": "070", "name": "Fidelity Bank"},
    {"code": "214", "name": "First City Monument Bank (FCMB)"},
    {"code": "221", "name": "Stanbic IBTC Bank"},
    {"code": "232", "name": "Sterling Bank"},
    {"code": "032", "name": "Union Bank of Nigeria"},
    {"code": "082", "name": "Keystone Bank"},
    {"code": "50515", "name": "Moniepoint Microfinance Bank"},
    {"code": "999991", "name": "OPay Digital Services"},
    {"code": "999992", "name": "Palmpay"},
    {"code": "50211", "name": "Kuda Microfinance Bank"},
    {"code": "51204", "name": "FairMoney Microfinance Bank"},
]


class WalletViewSet(viewsets.GenericViewSet):
    """
    API endpoint for managing virtual wallets, bank deposits, and withdrawals.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WalletSerializer

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get the current user's wallet (create if doesn't exist)."""
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(wallet)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], serializer_class=DepositSerializer)
    def deposit(self, request):
        """
        Deposit funds via card top-up or mock bank transfer gateway.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        reference = serializer.validated_data['reference']
        description = serializer.validated_data.get('description', 'Wallet Deposit')

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        if WalletTransaction.objects.filter(reference=reference).exists():
            return Response({'error': 'Duplicate transaction reference.'}, status=status.HTTP_400_BAD_REQUEST)

        wallet.balance += amount
        wallet.save()

        tx = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='deposit',
            amount=amount,
            reference=reference,
            description=description,
            status='completed'
        )

        return Response({
            'message': f'₦{amount:,.2f} deposited successfully!',
            'balance': str(wallet.balance),
            'transaction': WalletTransactionSerializer(tx).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], serializer_class=WithdrawalSerializer)
    def withdraw(self, request):
        """
        Submit a withdrawal payout request to a Nigerian bank account.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data['amount']
        bank_name = serializer.validated_data['bank_name']
        account_number = serializer.validated_data['account_number']
        account_name = serializer.validated_data['account_name']
        description = serializer.validated_data.get(
            'description',
            f"Withdrawal to {bank_name} - {account_number}"
        )

        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        if wallet.balance < amount:
            return Response(
                {"error": f"Insufficient balance. Your available balance is ₦{wallet.balance:,.2f}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Debit wallet balance
        wallet.balance -= amount
        wallet.save()

        ref = f"wdr_{uuid.uuid4().hex[:12]}"
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='withdrawal',
            amount=amount,
            reference=ref,
            description=description,
            status='completed',
            bank_name=bank_name,
            account_number=account_number,
            account_name=account_name
        )

        return Response({
            'message': f"Withdrawal of ₦{amount:,.2f} to {bank_name} ({account_number}) processed successfully.",
            'balance': str(wallet.balance),
            'transaction': WalletTransactionSerializer(tx).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """
        Returns full paginated transaction history with optional type filter.
        """
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        qs = wallet.transactions.all()

        tx_type = request.query_params.get('type')
        if tx_type:
            qs = qs.filter(transaction_type=tx_type)

        serializer = WalletTransactionSerializer(qs[:50], many=True)
        return Response({
            'count': qs.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def virtual_account(self, request):
        """Returns dedicated virtual account details for the authenticated user."""
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(wallet)
        return Response(serializer.data.get('virtual_account'))

    @action(detail=False, methods=['get'])
    def banks(self, request):
        """Returns list of supported Nigerian banks."""
        return Response(NIGERIAN_BANKS)
