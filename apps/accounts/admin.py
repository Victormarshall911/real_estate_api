"""Admin configuration for the accounts app."""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """Custom admin interface for the CustomUser model."""
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_email_verified', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_email_verified', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('id', 'date_joined', 'email_verification_token')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'role')}),
        ('Verification', {'fields': ('is_email_verified', 'email_verification_token')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('date_joined', 'last_login')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
