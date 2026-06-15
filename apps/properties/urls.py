"""
URL patterns for the properties app.
Mounted at /api/v1/properties/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'properties'

router = DefaultRouter()
router.register('', views.PropertyViewSet, basename='property')

urlpatterns = [
    path('', include(router.urls)),
]
