from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import LandlordProfile, LandlordReview
from .serializers import LandlordProfileSerializer, LandlordReviewSerializer


class IsLandlordOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'landlord'


class LandlordProfileViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoint for Landlord profiles.
    """
    queryset = LandlordProfile.objects.all()
    serializer_class = LandlordProfileSerializer
    permission_classes = [IsLandlordOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            search = self.request.query_params.get('search')
            if search:
                qs = qs.filter(user__first_name__icontains=search) | qs.filter(user__last_name__icontains=search)
        return qs.select_related('user').prefetch_related('reviews')

    @action(detail=False, methods=['get', 'post', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get, create, or update the authenticated landlord's profile."""
        if request.user.role != 'landlord':
            return Response(
                {'error': 'Only users with role "landlord" can manage a landlord profile.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.method == 'GET':
            try:
                profile = request.user.landlord_profile
                serializer = self.get_serializer(profile)
                return Response(serializer.data)
            except LandlordProfile.DoesNotExist:
                return Response({'error': 'Profile not created yet.'}, status=status.HTTP_404_NOT_FOUND)

        elif request.method in ['POST', 'PATCH']:
            profile, created = LandlordProfile.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            if not request.user.is_profile_complete:
                request.user.is_profile_complete = True
                request.user.save(update_fields=['is_profile_complete'])
            return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def rate(self, request, pk=None):
        """Submit a rating and review for a landlord."""
        landlord = self.get_object()
        if request.user == landlord.user:
            return Response({'error': 'You cannot rate your own profile.'}, status=status.HTTP_400_BAD_REQUEST)

        rating = request.data.get('rating')
        comment = request.data.get('comment', '')

        if not rating or not str(rating).isdigit() or int(rating) < 1 or int(rating) > 5:
            return Response({'error': 'Rating must be an integer between 1 and 5.'}, status=status.HTTP_400_BAD_REQUEST)

        review, created = LandlordReview.objects.update_or_create(
            landlord=landlord,
            reviewer=request.user,
            defaults={'rating': int(rating), 'comment': comment}
        )
        serializer = LandlordReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
