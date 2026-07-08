from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import DeveloperProfile, DeveloperReview
from .serializers import DeveloperProfileSerializer, DeveloperReviewSerializer


class IsDeveloperOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'developer'


class DeveloperProfileViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoint for Developer profiles.
    """
    queryset = DeveloperProfile.objects.all()
    serializer_class = DeveloperProfileSerializer
    permission_classes = [IsDeveloperOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            search = self.request.query_params.get('search')
            if search:
                qs = (
                    qs.filter(company_name__icontains=search) |
                    qs.filter(user__first_name__icontains=search) |
                    qs.filter(user__last_name__icontains=search)
                )
        return qs.select_related('user').prefetch_related('reviews')

    @action(detail=False, methods=['get', 'post', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get, create, or update the authenticated developer's profile."""
        if request.user.role != 'developer':
            return Response(
                {'error': 'Only users with role "developer" can manage a developer profile.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.method == 'GET':
            try:
                profile = request.user.developer_profile
                serializer = self.get_serializer(profile)
                return Response(serializer.data)
            except DeveloperProfile.DoesNotExist:
                return Response({'error': 'Profile not created yet.'}, status=status.HTTP_404_NOT_FOUND)

        elif request.method in ['POST', 'PATCH']:
            profile, created = DeveloperProfile.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            if not request.user.is_profile_complete:
                request.user.is_profile_complete = True
                request.user.save(update_fields=['is_profile_complete'])
            return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def rate(self, request, pk=None):
        """Submit a rating and review for a developer."""
        developer = self.get_object()
        if request.user == developer.user:
            return Response({'error': 'You cannot rate your own profile.'}, status=status.HTTP_400_BAD_REQUEST)

        rating = request.data.get('rating')
        comment = request.data.get('comment', '')

        if not rating or not str(rating).isdigit() or int(rating) < 1 or int(rating) > 5:
            return Response({'error': 'Rating must be an integer between 1 and 5.'}, status=status.HTTP_400_BAD_REQUEST)

        review, created = DeveloperReview.objects.update_or_create(
            developer=developer,
            reviewer=request.user,
            defaults={'rating': int(rating), 'comment': comment}
        )
        serializer = DeveloperReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
