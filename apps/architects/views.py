"""
API views for Architect Profile management and reviews.
"""
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ArchitectProfile, ArchitectReview
from .serializers import ArchitectProfileSerializer, ArchitectReviewSerializer


class IsArchitectOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'architect'


class ArchitectProfileViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoint for Architect profiles.
    Anyone can view verified architects. Only architects can create/update their profile.
    """
    queryset = ArchitectProfile.objects.all()
    serializer_class = ArchitectProfileSerializer
    permission_classes = [IsArchitectOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            # Optionally filter by specialization or query
            spec = self.request.query_params.get('specialization')
            if spec:
                qs = qs.filter(specialization__icontains=spec)
            search = self.request.query_params.get('search')
            if search:
                qs = qs.filter(company_name__icontains=search) | qs.filter(user__first_name__icontains=search)
        return qs.select_related('user').prefetch_related('reviews')

    @action(detail=False, methods=['get', 'post', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get, create, or update the authenticated architect's profile."""
        if request.user.role != 'architect':
            return Response(
                {'error': 'Only users with role "architect" can manage an architect profile.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.method == 'GET':
            try:
                profile = request.user.architect_profile
                serializer = self.get_serializer(profile)
                return Response(serializer.data)
            except ArchitectProfile.DoesNotExist:
                return Response({'error': 'Profile not created yet.'}, status=status.HTTP_404_NOT_FOUND)

        elif request.method in ['POST', 'PATCH']:
            profile, created = ArchitectProfile.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def rate(self, request, pk=None):
        """Submit a rating and review for an architect."""
        architect = self.get_object()
        if request.user == architect.user:
            return Response({'error': 'You cannot rate your own profile.'}, status=status.HTTP_400_BAD_REQUEST)

        rating = request.data.get('rating')
        comment = request.data.get('comment', '')

        if not rating or not str(rating).isdigit() or int(rating) < 1 or int(rating) > 5:
            return Response({'error': 'Rating must be an integer between 1 and 5.'}, status=status.HTTP_400_BAD_REQUEST)

        review, created = ArchitectReview.objects.update_or_create(
            architect=architect,
            reviewer=request.user,
            defaults={'rating': int(rating), 'comment': comment}
        )
        serializer = ArchitectReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
