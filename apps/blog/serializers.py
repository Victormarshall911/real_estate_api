"""
Serializers for Blog Posts and Categories.
"""
from rest_framework import serializers
from accounts.utils import get_clean_media_url
from .models import BlogPost, BlogCategory


class BlogCategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = BlogCategory
        fields = ['id', 'name', 'slug', 'description', 'post_count']

    def get_post_count(self, obj):
        return obj.posts.filter(status='published').count()


class BlogPostListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    author_name = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    tag_list = serializers.ReadOnlyField()

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'cover_image_url',
            'author_name', 'author_role', 'category_name', 'tag_list',
            'status', 'is_featured', 'read_time_minutes', 'view_count',
            'created_at', 'published_at',
        ]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.email
        return 'LandMarket Team'

    def get_author_role(self, obj):
        if obj.author:
            return obj.author.role
        return 'admin'

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_cover_image_url(self, obj):
        return get_clean_media_url(obj.cover_image, self.context.get('request'))


class BlogPostDetailSerializer(BlogPostListSerializer):
    """Full serializer for detail views."""

    class Meta(BlogPostListSerializer.Meta):
        fields = BlogPostListSerializer.Meta.fields + ['content']


class BlogPostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating blog posts."""

    class Meta:
        model = BlogPost
        fields = [
            'title', 'content', 'excerpt', 'cover_image',
            'category', 'tags', 'status', 'is_featured',
        ]

    def create(self, validated_data):
        request = self.context['request']
        validated_data['author'] = request.user
        if validated_data.get('status') == 'published':
            from django.utils import timezone
            validated_data['published_at'] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('status') == 'published' and not instance.published_at:
            from django.utils import timezone
            validated_data['published_at'] = timezone.now()
        return super().update(instance, validated_data)
