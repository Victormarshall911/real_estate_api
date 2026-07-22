"""
Blog Views — public listing/detail and admin management.
"""
from django.utils import timezone
from django.db.models import F
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import BlogPost, BlogCategory
from .serializers import (
    BlogPostListSerializer,
    BlogPostDetailSerializer,
    BlogPostCreateSerializer,
    BlogCategorySerializer,
)


class IsStaffOrAdminOrReadOnly(permissions.BasePermission):
    """
    Allows anyone to read. Write access requires staff or admin role.
    Also allows realtors to write their own posts.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff or request.user.role in ('admin', 'realtor')

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff or request.user.role == 'admin':
            return True
        # Realtors can only edit their own posts
        return obj.author == request.user


class BlogCategoryViewSet(viewsets.ModelViewSet):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    permission_classes = [IsStaffOrAdminOrReadOnly]
    lookup_field = 'slug'


class BlogPostViewSet(viewsets.ModelViewSet):
    """
    Public: list (published only), retrieve by slug.
    Authenticated staff/admin/realtor: create, update, delete.
    """
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        qs = BlogPost.objects.select_related('author', 'category').all()

        # Non-staff users only see published posts in list/retrieve
        if self.action in ('list', 'retrieve'):
            if not user or not user.is_authenticated or (
                not user.is_staff and user.role not in ('admin',)
            ):
                qs = qs.filter(status='published')
        return qs

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return BlogPostCreateSerializer
        if self.action == 'retrieve':
            return BlogPostDetailSerializer
        return BlogPostListSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'featured'):
            return [permissions.AllowAny()]
        return [IsStaffOrAdminOrReadOnly()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        BlogPost.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        qs = BlogPost.objects.filter(status='published', is_featured=True)[:6]
        serializer = BlogPostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsStaffOrAdminOrReadOnly])
    def my_posts(self, request):
        """Return the authenticated user's own posts (all statuses)."""
        qs = BlogPost.objects.filter(author=request.user).select_related('category')
        serializer = BlogPostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)
