from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Club

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
        
        user = User.objects.filter(email=email).first()
        if user and user.check_password(password):
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


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details."""
    class Meta:
        model = User
        fields = ["id", "email", "username", "profile_picture", "is_active"]
        read_only_fields = ["id", "is_active"]


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "password_confirm"]

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
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        """Create a new user."""
        validated_data.pop('password_confirm')
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
        user = User.objects.filter(email=data["email"]).first()
        if user and user.check_password(data["password"]):
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            
            refresh = RefreshToken.for_user(user)
            return {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            }
        raise serializers.ValidationError("Invalid email or password.")


class ClubSerializer(serializers.ModelSerializer):
    """Serializer for club details."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Club
        fields = [
            "id", "name", "sport", "logo", "location", "founded_year", 
            "venue_name", "website", "primary_color", "secondary_color", 
            "bio", "league", "selected_pack", "user_email"
        ]
        read_only_fields = ["id", "user_email"]

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


