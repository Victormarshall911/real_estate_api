from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from wallets.models import Wallet, WalletTransaction
from .models import EscrowTransaction
from .serializers import EscrowTransactionSerializer, EscrowCreateSerializer


class EscrowViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage the escrow transaction lifecycle.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            EscrowTransaction.objects
            .select_related('buyer', 'seller', 'property_listing')
            .filter(models.Q(buyer=user) | models.Q(seller=user))
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return EscrowCreateSerializer
        return EscrowTransactionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        instance = serializer.instance
        response_serializer = EscrowTransactionSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        seller = serializer.validated_data['seller']
        if seller == self.request.user:
            raise status.ValidationError("You cannot propose to buy your own property.")
        serializer.save(buyer=self.request.user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Seller accepts the pending proposal and locks the buyer's funds."""
        escrow = self.get_object()
        if escrow.seller != request.user:
            return Response(
                {"error": "Only the seller can accept this proposal."},
                status=status.HTTP_403_FORBIDDEN
            )
        if escrow.status != 'pending':
            return Response(
                {"error": "Only pending proposals can be accepted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        buyer_wallet, _ = Wallet.objects.get_or_create(user=escrow.buyer)
        if buyer_wallet.balance < escrow.amount:
            return Response(
                {"error": "Buyer has insufficient wallet balance to cover this purchase."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Lock funds by debiting buyer's wallet
        buyer_wallet.balance -= escrow.amount
        buyer_wallet.save()

        WalletTransaction.objects.create(
            wallet=buyer_wallet,
            transaction_type='payment',
            amount=escrow.amount,
            reference=f"escrow_lock_{escrow.id}",
            description=f"Locked in escrow for purchase of {escrow.property_listing.title}"
        )

        escrow.status = 'escrowed'
        escrow.save()
        
        serializer = self.get_serializer(escrow)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending deal (either party) or voluntarily refund escrowed funds (seller only)."""
        escrow = self.get_object()

        if escrow.status == 'pending':
            if request.user not in [escrow.buyer, escrow.seller]:
                return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
            
            escrow.status = 'cancelled'
            escrow.save()
            return Response({"message": "Proposal cancelled successfully."})

        elif escrow.status == 'escrowed':
            if escrow.seller != request.user:
                return Response(
                    {"error": "Only the seller can issue a refund after funds are locked in escrow. If you are the buyer, please raise a dispute."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Refund the buyer
            buyer_wallet, _ = Wallet.objects.get_or_create(user=escrow.buyer)
            buyer_wallet.balance += escrow.amount
            buyer_wallet.save()

            WalletTransaction.objects.create(
                wallet=buyer_wallet,
                transaction_type='refund',
                amount=escrow.amount,
                reference=f"escrow_refund_{escrow.id}",
                description=f"Refund from cancelled escrow for {escrow.property_listing.title}"
            )

            escrow.status = 'cancelled'
            escrow.save()
            return Response({"message": "Escrow transaction refunded and cancelled."})

        return Response(
            {"error": "Cannot cancel this transaction in its current status."},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def verify_milestone(self, request, pk=None):
        """Toggle verification flags for inspection or documentation."""
        escrow = self.get_object()
        if request.user not in [escrow.buyer, escrow.seller]:
            return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        milestone = request.data.get('milestone')
        value = request.data.get('value', True)

        if milestone == 'inspection':
            escrow.is_inspected = bool(value)
        elif milestone == 'documents':
            escrow.is_documents_verified = bool(value)
        else:
            return Response(
                {"error": "Invalid milestone. Must be 'inspection' or 'documents'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        escrow.save()
        serializer = self.get_serializer(escrow)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Authorize releasing the locked escrow funds to the seller."""
        escrow = self.get_object()
        if escrow.status not in ['escrowed', 'disputed']:
            return Response(
                {"error": "Only transactions with escrowed/disputed funds can be released."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if escrow.buyer != request.user and not request.user.is_staff:
            return Response(
                {"error": "Only the buyer (or an admin) can authorize releasing the funds."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Credit the seller's wallet
        seller_wallet, _ = Wallet.objects.get_or_create(user=escrow.seller)
        seller_wallet.balance += escrow.amount
        seller_wallet.save()

        WalletTransaction.objects.create(
            wallet=seller_wallet,
            transaction_type='receipt',
            amount=escrow.amount,
            reference=f"escrow_release_{escrow.id}",
            description=f"Received payment from escrow for {escrow.property_listing.title}"
        )

        # Mark listing as sold
        escrow.property_listing.status = 'sold'
        escrow.property_listing.save(update_fields=['status'])

        escrow.status = 'completed'
        escrow.buyer_approved = True
        escrow.save()

        return Response({"message": "Escrow funds released successfully. Property marked as sold."})

    @action(detail=True, methods=['post'])
    def dispute(self, request, pk=None):
        """Raise a dispute for administrative arbitration."""
        escrow = self.get_object()
        if escrow.status != 'escrowed':
            return Response(
                {"error": "Only active escrowed deals can be disputed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user not in [escrow.buyer, escrow.seller]:
            return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {"error": "A reason is required to raise a dispute."},
                status=status.HTTP_400_BAD_REQUEST
            )

        escrow.status = 'disputed'
        escrow.dispute_reason = reason
        escrow.save()

        return Response({"message": "Transaction flagged as disputed. Admin arbitration requested."})
