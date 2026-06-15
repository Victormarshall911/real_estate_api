"""Admin configuration for the properties app."""
from django.contrib import admin
from .models import PropertyListing, PropertyImage, PropertyView


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    readonly_fields = ('id', 'uploaded_at')


@admin.register(PropertyListing)
class PropertyListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'land_size', 'location', 'status', 'view_count', 'created_at')
    list_filter = ('status', 'state', 'created_at')
    search_fields = ('title', 'description', 'location', 'state')
    readonly_fields = ('id', 'view_count', 'search_vector', 'created_at', 'updated_at')
    raw_id_fields = ('realtor',)
    inlines = [PropertyImageInline]
    list_per_page = 25


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'caption', 'is_primary', 'uploaded_at')
    list_filter = ('is_primary',)
    raw_id_fields = ('property_listing',)


@admin.register(PropertyView)
class PropertyViewAdmin(admin.ModelAdmin):
    list_display = ('property_listing', 'viewer_ip', 'viewed_at')
    list_filter = ('viewed_at',)
    readonly_fields = ('id', 'property_listing', 'viewer_ip', 'user_agent', 'viewed_at')
    list_per_page = 50
