from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LandlordProfileViewSet

router = DefaultRouter()
router.register(r'profiles', LandlordProfileViewSet, basename='landlord-profiles')

urlpatterns = [
    path('', include(router.urls)),
]
