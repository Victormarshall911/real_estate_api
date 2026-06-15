"""
URL routing for Agents app.
Mounted at /api/v1/agents/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.AgentProfileViewSet, basename='agent_profile')
router.register(r'connections', views.AgentConnectionViewSet, basename='agent_connection')

urlpatterns = [
    path('', include(router.urls)),
]
