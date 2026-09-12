from django.contrib import admin
from .models import Wallet, WalletTransaction


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ('transaction_type', 'amount', 'reference', 'status', 'bank_name', 'account_number', 'created_at')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'balance', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [WalletTransactionInline]

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'wallet_user', 'transaction_type', 'amount', 'status', 'bank_name', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('reference', 'wallet__user__email', 'description', 'account_number', 'account_name')
    readonly_fields = ('id', 'created_at')

    def wallet_user(self, obj):
        return obj.wallet.user.email
    wallet_user.short_description = 'User Email'
