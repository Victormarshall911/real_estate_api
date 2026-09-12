"""
Serializers for user registration, authentication, profile display, and profile completion.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .utils import get_clean_media_url

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Read-only serializer for user data with verified tier badges."""
    full_name = serializers.CharField(read_only=True)
    has_realtor_profile = serializers.SerializerMethodField()
    has_agent_profile = serializers.SerializerMethodField()
    has_landlord_profile = serializers.SerializerMethodField()
    has_developer_profile = serializers.SerializerMethodField()
    is_fully_verified = serializers.BooleanField(read_only=True)
    profile_photo = serializers.SerializerMethodField()
    verification_level = serializers.SerializerMethodField()
    badge_label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_email_verified', 'date_joined',
            'has_realtor_profile', 'has_agent_profile', 'has_landlord_profile', 'has_developer_profile',
            'is_kyc_verified', 'is_profile_complete',
            'is_fully_verified', 'verification_level', 'badge_label',
            'date_of_birth', 'full_address', 'profile_photo',
        ]
        read_only_fields = fields

    def get_has_realtor_profile(self, obj):
        return hasattr(obj, 'realtor_profile')

    def get_has_agent_profile(self, obj):
        return hasattr(obj, 'agent_profile')

    def get_has_landlord_profile(self, obj):
        return hasattr(obj, 'landlord_profile')

    def get_has_developer_profile(self, obj):
        return hasattr(obj, 'developer_profile')

    def get_profile_photo(self, obj):
        return get_clean_media_url(obj.profile_photo, self.context.get('request'))

    def get_verification_level(self, obj):
        if hasattr(obj, 'kyc_verification'):
            kyc = obj.kyc_verification
            if kyc.status == 'verified':
                return 'cac_verified' if kyc.verification_type == 'cac_certificate' else 'id_verified'
        if obj.is_email_verified and getattr(obj, 'phone_number', None):
            return 'contact_verified'
        if obj.is_kyc_verified:
            return 'id_verified'
        return 'unverified'

    def get_badge_label(self, obj):
        level = self.get_verification_level(obj)
        mapping = {
            'cac_verified': 'CAC Registered Agency',
            'id_verified': 'Government ID Verified',
            'contact_verified': 'Contact Verified',
            'unverified': 'Unverified',
        }
        return mapping.get(level, 'Unverified')


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user personal account information."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'date_of_birth', 'full_address', 'profile_photo']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['profile_photo'] = get_clean_media_url(instance.profile_photo, self.context.get('request'))
        return ret


class CompleteProfileSerializer(serializers.ModelSerializer):
    """Serializer for the profile completion step (address, DOB, photo)."""

    class Meta:
        model = User
        fields = ['date_of_birth', 'full_address', 'profile_photo', 'is_profile_complete']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['profile_photo'] = get_clean_media_url(instance.profile_photo, self.context.get('request'))
        return ret

    def validate(self, attrs):
        """Ensure at minimum DOB and address are provided for standard buyers/realtors."""
        if self.instance.role in ['architect', 'agent', 'landlord', 'developer'] or attrs.get('is_profile_complete') is True:
            return attrs

        if not attrs.get('date_of_birth') and not self.instance.date_of_birth:
            raise serializers.ValidationError(
                {'date_of_birth': 'Date of birth is required to complete your profile.'}
            )
        if not attrs.get('full_address') and not self.instance.full_address:
            raise serializers.ValidationError(
                {'full_address': 'Address is required to complete your profile.'}
            )
        return attrs

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        dob = validated_data.get('date_of_birth', instance.date_of_birth)
        addr = validated_data.get('full_address', instance.full_address)
        if (dob and addr) or validated_data.get('is_profile_complete'):
            instance.is_profile_complete = True

        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    """Handles user registration with password validation."""
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )
    tokens = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'password', 'password_confirm', 'tokens',
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'required': True},
        }

    def validate_email(self, value):
        """Ensure email is unique (case-insensitive)."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate(self, attrs):
        """Ensure passwords match."""
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError(
                {'password_confirm': 'Passwords do not match.'}
            )
        return attrs

    def get_tokens(self, user):
        """Generate JWT token pair for newly registered user."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def create(self, validated_data):
        """Create user and hash password."""
        return User.objects.create_user(**validated_data)


class EmailVerifySerializer(serializers.Serializer):
    """Serializer for email verification token."""
    token = serializers.UUIDField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError('Invalid email or password.')

        if not user.is_active:
            raise serializers.ValidationError('This account has been deactivated.')

        refresh = RefreshToken.for_user(user)
        return {
            'user': UserSerializer(user, context=self.context).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
