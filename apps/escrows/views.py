import uuid
from django.utils import timezone
from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from wallets.models import Wallet, WalletTransaction
from .models import EscrowTransaction, EscrowMediation
from .serializers import EscrowTransactionSerializer, EscrowCreateSerializer, EscrowMediationSerializer


class EscrowViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage the escrow transaction lifecycle, dual confirmation,
    and automatic dispute mediation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return EscrowTransaction.objects.select_related('buyer', 'seller', 'property_listing').all()
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
            raise serializers.ValidationError("You cannot propose to buy your own property.")
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

        elif escrow.status in ['escrowed', 'in_mediation']:
            if escrow.seller != request.user and not request.user.is_staff:
                return Response(
                    {"error": "Only the seller or compliance team can issue a refund after funds are locked in escrow."},
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
                reference=f"escrow_refund_{escrow.id}_{int(timezone.now().timestamp())}",
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
    def confirm(self, request, pk=None):
        """
        Dual confirmation action:
        - Buyer presses confirmed -> buyer_confirmed = True
        - Seller presses confirmed -> seller_confirmed = True
        - If BOTH confirmed -> completed! Funds disbursed to seller wallet, property marked sold.
        - If one confirmed and other already rejected -> stays in mediation.
        """
        escrow = self.get_object()
        if escrow.status not in ['escrowed', 'in_mediation']:
            return Response(
                {"error": "Confirmation is only available for active escrowed transactions."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user not in [escrow.buyer, escrow.seller]:
            return Response({"error": "Only the buyer or seller can confirm completion."}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        is_buyer = request.user == escrow.buyer
        is_seller = request.user == escrow.seller

        if is_buyer:
            escrow.buyer_confirmed = True
            escrow.buyer_confirmed_at = now
            escrow.buyer_approved = True
        elif is_seller:
            escrow.seller_confirmed = True
            escrow.seller_confirmed_at = now
            escrow.seller_approved = True

        # Check if BOTH have confirmed
        if escrow.buyer_confirmed and escrow.seller_confirmed:
            # Credit the seller's wallet
            seller_wallet, _ = Wallet.objects.get_or_create(user=escrow.seller)
            seller_wallet.balance += escrow.amount
            seller_wallet.save()

            WalletTransaction.objects.create(
                wallet=seller_wallet,
                transaction_type='receipt',
                amount=escrow.amount,
                reference=f"escrow_release_{escrow.id}_{int(now.timestamp())}",
                description=f"Received payment from escrow for {escrow.property_listing.title}"
            )

            # Mark listing as sold
            escrow.property_listing.status = 'sold'
            escrow.property_listing.save(update_fields=['status'])

            escrow.status = 'completed'
            escrow.in_mediation = False
            escrow.mediation_status = 'resolved'
            escrow.mediation_resolved_at = now
            escrow.mediation_resolution_notes = "Resolved automatically upon mutual dual-confirmation by buyer and seller."
            escrow.save()

            serializer = self.get_serializer(escrow)
            return Response({
                "message": "Both parties confirmed! Escrow funds released to seller and deal marked complete.",
                "escrow": serializer.data
            }, status=status.HTTP_200_OK)

        escrow.save()
        serializer = self.get_serializer(escrow)
        waiting_on = "seller" if is_buyer else "buyer"
        return Response({
            "message": f"Confirmation recorded successfully. Waiting for the {waiting_on} to confirm.",
            "escrow": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject_confirmation(self, request, pk=None):
        """
        Triggered when a buyer or seller refuses confirmation or flags an issue.
        Immediately opens a mediation case and assigns the LandMarket team.
        """
        escrow = self.get_object()
        if request.user not in [escrow.buyer, escrow.seller]:
            return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        reason = request.data.get('reason', '').strip()
        evidence_notes = request.data.get('evidence_notes', '').strip()

        if not reason:
            return Response({"error": "A specific reason is required to reject confirmation or report an issue."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        is_buyer = request.user == escrow.buyer
        party_name = "Buyer" if is_buyer else "Seller"

        # Update escrow state
        escrow.status = 'in_mediation'
        escrow.in_mediation = True
        escrow.mediation_status = 'opened'
        escrow.mediation_reason = f"{party_name} ({request.user.email}) rejected confirmation: {reason}"
        escrow.mediation_opened_at = now

        if is_buyer:
            escrow.buyer_confirmed = False
        else:
            escrow.seller_confirmed = False

        escrow.save()

        # Create mediation record
        case_no = f"MED-{uuid.uuid4().hex[:8].upper()}"
        mediation = EscrowMediation.objects.create(
            escrow=escrow,
            case_number=case_no,
            initiated_by=request.user,
            reason=reason,
            evidence_notes=evidence_notes,
            status='opened',
            assigned_team='LandMarket Trust & Compliance Team'
        )

        serializer = self.get_serializer(escrow)
        return Response({
            "message": f"Mediation opened (Case #{case_no}). The LandMarket Trust & Safety team has been assigned to arbitrate.",
            "case_number": case_no,
            "escrow": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def dispute(self, request, pk=None):
        """Alias for raising a formal dispute / mediation request."""
        return self.reject_confirmation(request, pk)

    @action(detail=True, methods=['post'])
    def resolve_mediation(self, request, pk=None):
        """
        Compliance / Admin endpoint to arbitrate an in-mediation escrow deal.
        Resolution actions:
        - 'refund_buyer': Return full funds to buyer
        - 'release_seller': Disburse funds to seller
        - 'split': Split funds (50/50 or custom)
        """
        if not request.user.is_staff:
            return Response({"error": "Only LandMarket Compliance administrators can arbitrate mediations."}, status=status.HTTP_403_FORBIDDEN)

        escrow = self.get_object()
        resolution_type = request.data.get('resolution')
        notes = request.data.get('notes', 'Resolved by administrative compliance decision.')
        now = timezone.now()

        if resolution_type == 'refund_buyer':
            buyer_wallet, _ = Wallet.objects.get_or_create(user=escrow.buyer)
            buyer_wallet.balance += escrow.amount
            buyer_wallet.save()

            WalletTransaction.objects.create(
                wallet=buyer_wallet,
                transaction_type='refund',
                amount=escrow.amount,
                reference=f"med_refund_{escrow.id}_{int(now.timestamp())}",
                description=f"Mediation resolution refund for {escrow.property_listing.title}"
            )
            escrow.status = 'cancelled'

        elif resolution_type == 'release_seller':
            seller_wallet, _ = Wallet.objects.get_or_create(user=escrow.seller)
            seller_wallet.balance += escrow.amount
            seller_wallet.save()

            WalletTransaction.objects.create(
                wallet=seller_wallet,
                transaction_type='receipt',
                amount=escrow.amount,
                reference=f"med_release_{escrow.id}_{int(now.timestamp())}",
                description=f"Mediation resolution disbursement for {escrow.property_listing.title}"
            )
            escrow.property_listing.status = 'sold'
            escrow.property_listing.save(update_fields=['status'])
            escrow.status = 'completed'

        elif resolution_type == 'split':
            half = escrow.amount / 2
            buyer_wallet, _ = Wallet.objects.get_or_create(user=escrow.buyer)
            buyer_wallet.balance += half
            buyer_wallet.save()

            seller_wallet, _ = Wallet.objects.get_or_create(user=escrow.seller)
            seller_wallet.balance += half
            seller_wallet.save()

            WalletTransaction.objects.create(
                wallet=buyer_wallet,
                transaction_type='refund',
                amount=half,
                reference=f"med_split_b_{escrow.id}_{int(now.timestamp())}",
                description=f"Mediation 50% settlement refund for {escrow.property_listing.title}"
            )
            WalletTransaction.objects.create(
                wallet=seller_wallet,
                transaction_type='receipt',
                amount=half,
                reference=f"med_split_s_{escrow.id}_{int(now.timestamp())}",
                description=f"Mediation 50% settlement payment for {escrow.property_listing.title}"
            )
            escrow.status = 'completed'
        else:
            return Response({"error": "Invalid resolution type. Must be refund_buyer, release_seller, or split."}, status=status.HTTP_400_BAD_REQUEST)

        escrow.in_mediation = False
        escrow.mediation_status = 'resolved'
        escrow.mediation_resolved_at = now
        escrow.mediation_resolution_notes = notes
        escrow.save()

        # Update all active mediation records for this escrow
        escrow.mediations.filter(status__in=['opened', 'in_review']).update(
            status='resolved',
            resolution=resolution_type,
            resolution_notes=notes,
            resolved_at=now
        )

        serializer = self.get_serializer(escrow)
        return Response({
            "message": f"Mediation case resolved with action '{resolution_type}'.",
            "escrow": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Legacy direct release or staff release."""
        return self.confirm(request, pk)
