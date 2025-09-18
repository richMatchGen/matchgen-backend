import logging
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

logger = logging.getLogger(__name__)
from .models import (
    User, Club, UserRole, ClubMembership, Feature, 
    SubscriptionTierFeature, AuditLog
)
from .permissions import FeaturePermission, get_user_role_in_club


User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer that works with email-based authentication."""
    
    def validate(self, attrs):
        # Use email instead of username
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError("Must include 'email' and 'password'.")
        
        # Validate email format
        if '@' not in email:
            raise serializers.ValidationError("Please provide a valid email address.")
        
        try:
            # Try to get user using Django ORM first
            user = User.objects.filter(email=email).first()
            if not user:
                # Fallback: try to get user with raw SQL if ORM fails
                logger.warning(f"User not found via ORM for email: {email}")
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id, email, username, profile_picture, is_active, password FROM users_user WHERE email = %s", [email])
                    row = cursor.fetchone()
                    if row:
                        user = User()
                        user.id = row[0]
                        user.email = row[1]
                        user.username = row[2]
                        user.profile_picture = row[3]
                        user.is_active = row[4]
                        user.password = row[5]  # Store password for manual checking
                    else:
                        user = None
        except Exception as e:
            logger.error(f"Database error during user lookup: {str(e)}", exc_info=True)
            raise serializers.ValidationError("Database error occurred. Please try again.")
        
        if user:
            # Check password - handle both Django ORM and manual user objects
            if hasattr(user, 'check_password'):
                password_valid = user.check_password(password)
            else:
                # Manual password checking for raw SQL user objects
                from django.contrib.auth.hashers import check_password
                password_valid = check_password(password, user.password)
            
            if password_valid:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                
                refresh = self.get_token(user)
                data = {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'profile_picture': user.profile_picture
                    },
                }
                return data
            else:
                raise serializers.ValidationError("Invalid email or password.")
        else:
            raise serializers.ValidationError("Invalid email or password.")


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details."""
    class Meta:
        model = User
        fields = ["id", "email", "username", "profile_picture", "is_active", "email_verified"]
        read_only_fields = ["id", "is_active"]


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "password2"]

    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        """Validate password strength."""
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        
        if not any(c.islower() for c in value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")
        
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Password must contain at least one digit.")
        
        return value

    def validate(self, data):
        """Validate password confirmation."""
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        """Create a new user."""
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data.get("username"),
            password=validated_data["password"]
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        """Validate email format."""
        if '@' not in value:
            raise serializers.ValidationError("Please provide a valid email address.")
        return value

    def validate(self, data):
        """Validate login credentials."""
        try:
            user = User.objects.filter(email=data["email"]).first()
        except Exception as e:
            # Handle case where email verification fields don't exist
            logger.warning(f"Database fields not available: {str(e)}")
            # Try to get user with only basic fields
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, email, username, profile_picture, is_active, password FROM users_user WHERE email = %s", [data["email"]])
                row = cursor.fetchone()
                if row:
                    user = User()
                    user.id = row[0]
                    user.email = row[1]
                    user.username = row[2]
                    user.profile_picture = row[3]
                    user.is_active = row[4]
                    user.password = row[5]  # Store password for manual checking
                else:
                    user = None
        
        if user:
            # Check password - handle both Django ORM and manual user objects
            if hasattr(user, 'check_password'):
                password_valid = user.check_password(data["password"])
            else:
                # Manual password checking for raw SQL user objects
                from django.contrib.auth.hashers import check_password
                password_valid = check_password(data["password"], user.password)
            
            if password_valid:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                
                refresh = RefreshToken.for_user(user)
                return {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": UserSerializer(user).data,
                }
            else:
                raise serializers.ValidationError("Invalid email or password.")
        else:
            raise serializers.ValidationError("Invalid email or password.")


class ClubSerializer(serializers.ModelSerializer):
    """Serializer for club details."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_role = serializers.SerializerMethodField()
    available_features = serializers.SerializerMethodField()
    
    class Meta:
        model = Club
        fields = [
            "id", "name", "sport", "logo", "location", "founded_year", 
            "venue_name", "website", "primary_color", "secondary_color", 
            "bio", "league", "selected_pack", "user_email", "user_role", "available_features",
            "subscription_tier", "subscription_active", "subscription_start_date", "subscription_end_date"
        ]
        read_only_fields = ["id", "user_email", "subscription_start_date"]

    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return get_user_role_in_club(request.user, obj)
        return None
    
    def get_available_features(self, obj):
        return FeaturePermission.get_available_features(obj)

    def validate_name(self, value):
        """Validate club name."""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Club name must be at least 2 characters long.")
        return value.strip()

    def validate_sport(self, value):
        """Validate sport field."""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Sport must be at least 2 characters long.")
        return value.strip()

    def validate_logo(self, value):
        """Validate logo field - accept URLs or base64 data URLs."""
        if not value:
            return value
        
        # Accept base64 data URLs
        if value.startswith('data:image/'):
            return value
        
        # Accept regular URLs
        if value.startswith(('http://', 'https://')):
            return value
        
        raise serializers.ValidationError("Logo must be a valid URL or base64 data URL.")

    def validate_website(self, value):
        """Validate website URL."""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Please provide a valid URL starting with http:// or https://")
        return value

    def validate_primary_color(self, value):
        """Validate primary color hex format."""
        if value and not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Primary color must be a valid hex color (e.g., #FF0000)")
        return value

    def validate_secondary_color(self, value):
        """Validate secondary color hex format."""
        if value and not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Secondary color must be a valid hex color (e.g., #FF0000)")
        return value


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = ('id', 'name', 'description')


class ClubMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    role = UserRoleSerializer(read_only=True)
    invited_by = UserSerializer(read_only=True)
    role_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ClubMembership
        fields = (
            'id', 'user', 'club', 'role', 'status', 'invited_by',
            'invited_at', 'accepted_at', 'role_id'
        )
        read_only_fields = ('id', 'user', 'club', 'invited_by', 'invited_at', 'accepted_at')
    
    def create(self, validated_data):
        role_id = validated_data.pop('role_id')
        try:
            role = UserRole.objects.get(id=role_id)
        except UserRole.DoesNotExist:
            raise serializers.ValidationError("Invalid role ID")
        
        validated_data['role'] = role
        return super().create(validated_data)


class InviteUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role_id = serializers.IntegerField()
    message = serializers.CharField(required=False, allow_blank=True)
    
    def validate_email(self, value):
        # Check if user already has membership in this club
        club = self.context.get('club')
        try:
            user = User.objects.get(email=value)
            if ClubMembership.objects.filter(user=user, club=club).exists():
                raise serializers.ValidationError("User is already a member of this club")
        except User.DoesNotExist:
            # User doesn't exist yet, which is fine for invites
            pass
        return value
    
    def validate_role_id(self, value):
        try:
            UserRole.objects.get(id=value)
        except UserRole.DoesNotExist:
            raise serializers.ValidationError("Invalid role ID")
        return value


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ('id', 'name', 'code', 'description', 'is_active')


class SubscriptionTierFeatureSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer(read_only=True)
    
    class Meta:
        model = SubscriptionTierFeature
        fields = ('id', 'subscription_tier', 'feature')


class AuditLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    club = ClubSerializer(read_only=True)
    
    class Meta:
        model = AuditLog
        fields = (
            'id', 'user', 'club', 'action', 'details', 'ip_address',
            'user_agent', 'timestamp'
        )
        read_only_fields = ('id', 'user', 'club', 'action', 'details', 'ip_address', 'user_agent', 'timestamp')


class TeamManagementSerializer(serializers.Serializer):
    """Serializer for team management data"""
    members = ClubMembershipSerializer(many=True, read_only=True)
    available_roles = UserRoleSerializer(many=True, read_only=True)
    can_manage_members = serializers.BooleanField(read_only=True)
    can_manage_billing = serializers.BooleanField(read_only=True)


class FeatureAccessSerializer(serializers.Serializer):
    """Serializer for feature access information"""
    available_features = serializers.ListField(child=serializers.CharField(), read_only=True)
    subscription_tier = serializers.CharField(read_only=True)
    subscription_active = serializers.BooleanField(read_only=True)
    feature_access = serializers.DictField(read_only=True)  # feature_code: has_access


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])


