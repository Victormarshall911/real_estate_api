import hashlib
from rest_framework import serializers
from .models import Wallet, WalletTransaction


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'transaction_type', 'amount', 'reference',
            'description', 'status', 'bank_name', 'account_number',
            'account_name', 'created_at'
        ]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    transactions = WalletTransactionSerializer(many=True, read_only=True)
    locked_in_escrow = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    virtual_account = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'locked_in_escrow', 'virtual_account', 'created_at', 'updated_at', 'transactions']
        read_only_fields = fields

    def get_virtual_account(self, obj):
        """Generates deterministic virtual account details for bank transfer deposits."""
        user = obj.user
        # Generate clean 10-digit account number from user uuid/email
        raw_num = int(hashlib.md5(f"wm_{user.id}".encode('utf-8')).hexdigest()[:8], 16)
        acct_num = f"9{str(raw_num).zfill(9)[:9]}"
        
        full_name = user.full_name or f"{user.first_name} {user.last_name}".strip() or user.email.split('@')[0]
        return {
            'bank_name': 'Wema Bank (Virtual Transfer)',
            'secondary_bank': 'Providus Bank',
            'account_number': acct_num,
            'account_name': f"LandMarket / {full_name}",
            'currency': 'NGN',
            'instruction': 'Make a direct bank transfer to this dedicated account to instantly fund your LandMarket wallet.'
        }


class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=100)
    reference = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class WithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=500)
    bank_name = serializers.CharField(max_length=100)
    account_number = serializers.CharField(max_length=20, min_length=10)
    account_name = serializers.CharField(max_length=150)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_account_number(self, value):
        v = value.strip()
        if not v.isdigit() or len(v) != 10:
            raise serializers.ValidationError("Nigerian NUBAN bank account number must be exactly 10 digits.")
        return v
