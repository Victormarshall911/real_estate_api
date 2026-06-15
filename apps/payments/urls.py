"""
URL patterns for the payments app.
Mounted at /api/v1/payments/
"""
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('initiate/', views.InitiatePaymentView.as_view(), name='initiate'),
    path('webhook/', views.PaystackWebhookView.as_view(), name='webhook'),
    path('history/', views.PaymentHistoryView.as_view(), name='history'),
]
