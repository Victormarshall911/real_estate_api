"""Admin configuration for the realtors app."""
from django.contrib import admin
from .models import RealtorProfile


@admin.register(RealtorProfile)
class RealtorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'phone_number', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'company_name')
    readonly_fields = ('id', 'total_views', 'created_at', 'updated_at')
    raw_id_fields = ('user',)
