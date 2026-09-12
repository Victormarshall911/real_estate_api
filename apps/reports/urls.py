from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CrimeReportViewSet

router = DefaultRouter()
router.register(r'crime', CrimeReportViewSet, basename='crime-report')

urlpatterns = [
    path('', include(router.urls)),
]
