from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BlogPostViewSet, BlogCategoryViewSet

router = DefaultRouter()
router.register(r'posts', BlogPostViewSet, basename='blog-posts')
router.register(r'categories', BlogCategoryViewSet, basename='blog-categories')

urlpatterns = [
    path('', include(router.urls)),
]
