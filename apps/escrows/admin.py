from django.contrib import admin
from django.utils import timezone
from .models import EscrowTransaction, EscrowMediation
from wallets.models import Wallet, WalletTransaction


class EscrowMediationInline(admin.TabularInline):
    model = EscrowMediation
    extra = 0
    readonly_fields = ('case_number', 'initiated_by', 'reason', 'status', 'created_at')


@admin.register(EscrowTransaction)
class EscrowTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'buyer', 'seller', 'property_listing', 'amount',
        'status', 'buyer_confirmed', 'seller_confirmed',
        'in_mediation', 'mediation_status', 'created_at'
    )
    list_filter = ('status', 'in_mediation', 'buyer_confirmed', 'seller_confirmed', 'created_at')
    search_fields = ('id', 'buyer__email', 'seller__email', 'property_listing__title', 'mediation_reason')
    readonly_fields = ('id', 'created_at', 'updated_at', 'mediation_opened_at', 'mediation_resolved_at')
    inlines = [EscrowMediationInline]
    actions = ['admin_release_to_seller', 'admin_refund_to_buyer']

    def admin_release_to_seller(self, request, queryset):
        count = 0
        now = timezone.now()
        for escrow in queryset.filter(status__in=['escrowed', 'in_mediation']):
            seller_wallet, _ = Wallet.objects.get_or_create(user=escrow.seller)
            seller_wallet.balance += escrow.amount
            seller_wallet.save()

            WalletTransaction.objects.create(
                wallet=seller_wallet,
                transaction_type='receipt',
                amount=escrow.amount,
                reference=f"admin_release_{escrow.id}_{int(now.timestamp())}",
                description=f"Admin released escrow funds for {escrow.property_listing.title}"
            )
            escrow.status = 'completed'
            escrow.in_mediation = False
            escrow.mediation_status = 'resolved'
            escrow.mediation_resolved_at = now
            escrow.save()
            count += 1
        self.message_user(request, f"Successfully released funds to seller for {count} escrow transactions.")
    admin_release_to_seller.short_description = "Arbitrate & Release Funds to Seller"

    def admin_refund_to_buyer(self, request, queryset):
        count = 0
        now = timezone.now()
        for escrow in queryset.filter(status__in=['escrowed', 'in_mediation']):
            buyer_wallet, _ = Wallet.objects.get_or_create(user=escrow.buyer)
            buyer_wallet.balance += escrow.amount
            buyer_wallet.save()

            WalletTransaction.objects.create(
                wallet=buyer_wallet,
                transaction_type='refund',
                amount=escrow.amount,
                reference=f"admin_refund_{escrow.id}_{int(now.timestamp())}",
                description=f"Admin refunded escrow funds for {escrow.property_listing.title}"
            )
            escrow.status = 'cancelled'
            escrow.in_mediation = False
            escrow.mediation_status = 'resolved'
            escrow.mediation_resolved_at = now
            escrow.save()
            count += 1
        self.message_user(request, f"Successfully refunded {count} escrow transactions back to buyers.")
    admin_refund_to_buyer.short_description = "Arbitrate & Refund Funds to Buyer"


@admin.register(EscrowMediation)
class EscrowMediationAdmin(admin.ModelAdmin):
    list_display = ('case_number', 'escrow', 'initiated_by', 'status', 'resolution', 'assigned_team', 'created_at')
    list_filter = ('status', 'resolution', 'created_at')
    search_fields = ('case_number', 'reason', 'evidence_notes', 'initiated_by__email')
    readonly_fields = ('id', 'case_number', 'created_at', 'resolved_at')
