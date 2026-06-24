from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Wallet, WalletTransaction
from .serializers import WalletSerializer, WalletTransactionSerializer, DepositSerializer

class WalletViewSet(viewsets.GenericViewSet):
    """
    API endpoint for managing virtual wallets.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WalletSerializer

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get the current user's wallet (create if doesn't exist)."""
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(wallet)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], serializer_class=DepositSerializer)
    def deposit(self, request):
        """
        Mock endpoint to deposit funds. In production, this would be a webhook 
        from Paystack or Flutterwave after successful payment.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        reference = serializer.validated_data['reference']
        description = serializer.validated_data.get('description', 'Wallet Deposit')

        wallet, created = Wallet.objects.get_or_create(user=request.user)
        
        if WalletTransaction.objects.filter(reference=reference).exists():
            return Response({'error': 'Duplicate transaction reference.'}, status=status.HTTP_400_BAD_REQUEST)

        wallet.balance += amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='deposit',
            amount=amount,
            reference=reference,
            description=description
        )

        return Response({
            'message': 'Deposit successful',
            'balance': str(wallet.balance)
        }, status=status.HTTP_200_OK)
