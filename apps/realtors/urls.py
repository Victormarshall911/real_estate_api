"""
URL patterns for the realtors app.
Mounted at /api/v1/realtors/
"""
from django.urls import path
from . import views

app_name = 'realtors'

urlpatterns = [
    path('', views.RealtorProfileListView.as_view(), name='realtor_list'),
    path('profile/', views.RealtorProfileCreateView.as_view(), name='realtor_create'),
    path('profile/update/', views.RealtorProfileUpdateView.as_view(), name='realtor_update'),
    path('<uuid:id>/', views.RealtorProfileDetailView.as_view(), name='realtor_detail'),
]
