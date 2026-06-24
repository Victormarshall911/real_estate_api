"""
Root URL configuration for Real Estate API.
All API routes are versioned under /api/v1/.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/properties/', include('properties.urls')),
    path('api/v1/realtors/', include('realtors.urls')),
    path('api/v1/payments/', include('payments.urls')),
    path('api/v1/kyc/', include('kyc.urls')),
    path('api/v1/agents/', include('agents.urls')),
    path('api/v1/subscriptions/', include('subscriptions.urls')),
    path('api/v1/wallets/', include('apps.wallets.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
