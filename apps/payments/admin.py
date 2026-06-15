"""Admin configuration for the payments app."""
from django.contrib import admin
from .models import PaystackPayment


@admin.register(PaystackPayment)
class PaystackPaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'payment_type', 'amount', 'reference', 'status', 'created_at')
    list_filter = ('status', 'payment_type', 'created_at')
    search_fields = ('reference', 'user__email')
    readonly_fields = ('id', 'reference', 'paystack_transaction_id', 'metadata', 'created_at', 'updated_at')
    raw_id_fields = ('user',)
