from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EscrowViewSet

router = DefaultRouter()
router.register('', EscrowViewSet, basename='escrow')

urlpatterns = [
    path('', include(router.urls)),
]
