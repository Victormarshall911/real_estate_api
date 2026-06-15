"""
URL routing for Subscriptions app.
Mounted at /api/v1/subscriptions/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'plans', views.SubscriptionPlanViewSet, basename='subscription_plan')
router.register(r'my', views.UserSubscriptionViewSet, basename='user_subscription')

urlpatterns = [
    path('', include(router.urls)),
]
