"""
URL patterns for the accounts app.
Mounted at /api/v1/auth/
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-email/', views.EmailVerifyView.as_view(), name='verify_email'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('complete-profile/', views.CompleteProfileView.as_view(), name='complete_profile'),
    path('upgrade-to-realtor/', views.UpgradeToRealtorView.as_view(), name='upgrade_to_realtor'),
]
