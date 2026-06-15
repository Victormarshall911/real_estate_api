"""
Views for Realtor Profile retrieval and management.
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from accounts.permissions import IsRealtorOnly
from .models import RealtorProfile
from .serializers import RealtorProfileSerializer, RealtorProfileCreateSerializer


class RealtorProfileDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/realtors/<id>/
    Public endpoint to view a realtor's profile with their listings.
    Uses select_related to avoid N+1 on user data.
    """
    queryset = RealtorProfile.objects.select_related('user').prefetch_related(
        'properties__images'
    )
    serializer_class = RealtorProfileSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'


class RealtorProfileListView(generics.ListAPIView):
    """
    GET /api/v1/realtors/
    Public listing of all verified realtors.
    """
    queryset = RealtorProfile.objects.select_related('user').filter(
        is_verified=True
    )
    serializer_class = RealtorProfileSerializer
    permission_classes = [permissions.AllowAny]


class RealtorProfileCreateView(generics.CreateAPIView):
    """
    POST /api/v1/realtors/profile/
    Authenticated realtors can create their profile.
    """
    serializer_class = RealtorProfileCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsRealtorOnly]

    def create(self, request, *args, **kwargs):
        # Check if profile already exists
        if hasattr(request.user, 'realtor_profile'):
            return Response(
                {'error': 'You already have a realtor profile.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)


class RealtorProfileUpdateView(generics.UpdateAPIView):
    """
    PUT/PATCH /api/v1/realtors/profile/update/
    Authenticated realtors can update their own profile.
    """
    serializer_class = RealtorProfileCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsRealtorOnly]

    def get_object(self):
        return self.request.user.realtor_profile
