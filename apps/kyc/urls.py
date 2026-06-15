"""
URL patterns for the KYC app.
Mounted at /api/v1/kyc/
"""
from django.urls import path
from . import views

app_name = 'kyc'

urlpatterns = [
    path('initiate/', views.InitiateKYCView.as_view(), name='initiate'),
    path('status/', views.KYCStatusView.as_view(), name='status'),
    path('webhook/', views.DojahWebhookView.as_view(), name='webhook'),
]
