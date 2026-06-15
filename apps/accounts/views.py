"""
Views for user registration, email verification, profile retrieval, and profile completion.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import RegisterSerializer, UserSerializer, EmailVerifySerializer, CompleteProfileSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    Creates a new user account and returns JWT tokens.
    Sends email verification link.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'anon'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send verification email (non-blocking — fails silently in dev)
        self._send_verification_email(user)

        return Response(
            {
                'user': UserSerializer(user).data,
                'tokens': serializer.get_tokens(user),
                'message': 'Registration successful. Please verify your email.',
            },
            status=status.HTTP_201_CREATED,
        )

    def _send_verification_email(self, user):
        """Send email verification link. Fails silently if email is not configured."""
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={user.email_verification_token}"
        subject = 'Verify your LandMarket account'
        message = (
            f"Hi {user.first_name},\n\n"
            f"Welcome to LandMarket! Please verify your email by clicking:\n"
            f"{verify_url}\n\n"
            f"If you didn't create this account, you can ignore this email.\n\n"
            f"— The LandMarket Team"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass


class EmailVerifyView(APIView):
    """
    POST /api/v1/auth/verify-email/
    Verifies user email using the token from the verification link.
    """
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'anon'

    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        try:
            user = User.objects.get(email_verification_token=token, is_email_verified=False)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired verification token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])

        return Response(
            {'message': 'Email verified successfully.'},
            status=status.HTTP_200_OK,
        )


class LoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Standard JWT token obtain view (email + password → access + refresh tokens).
    """
    throttle_scope = 'anon'


class UserProfileView(generics.RetrieveAPIView):
    """
    GET /api/v1/auth/profile/
    Returns the authenticated user's profile data.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CompleteProfileView(generics.UpdateAPIView):
    """
    PUT/PATCH /api/v1/auth/complete-profile/
    Allows authenticated users to complete their profile with DOB, address, and photo.
    """
    serializer_class = CompleteProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {
                'message': 'Profile updated successfully.',
                'user': UserSerializer(instance).data,
            },
            status=status.HTTP_200_OK,
        )
