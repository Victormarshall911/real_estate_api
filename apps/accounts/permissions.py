"""
Custom permission classes for role-based and object-level access control.
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission: only the owner can modify the object.
    Assumes the object has a `user` attribute or a `realtor.user` chain.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check direct user ownership
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # Check ownership through realtor profile
        if hasattr(obj, 'realtor'):
            return obj.realtor.user == request.user

        return False


class IsRealtorOnly(permissions.BasePermission):
    """
    Allows access only to users with the 'realtor' role.
    """
    message = 'Only realtors can perform this action.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'realtor'
        )


class IsAdminOnly(permissions.BasePermission):
    """
    Allows access only to users with the 'admin' role.
    """
    message = 'Only admins can perform this action.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )
