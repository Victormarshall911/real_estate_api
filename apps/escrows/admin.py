from django.contrib import admin
from .models import EscrowTransaction


@admin.register(EscrowTransaction)
class EscrowTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'seller', 'property_listing', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'buyer__email', 'seller__email', 'property_listing__title')
