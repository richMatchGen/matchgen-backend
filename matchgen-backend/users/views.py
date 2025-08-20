import logging
import base64
import requests
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.core.cache import cache

from .models import Club, User
from .serializers import (
    ClubSerializer,
    CustomTokenObtainPairSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

# Simple rate limiting for debugging
class RateLimitMixin:
    def check_rate_limit(self, user_id, endpoint, limit_seconds=5):
        """Simple rate limiting to prevent excessive calls."""
        cache_key = f"rate_limit_{endpoint}_{user_id}"
        last_call = cache.get(cache_key)
        current_time = timezone.now()
        
        if last_call:
            time_diff = (current_time - last_call).total_seconds()
            if time_diff < limit_seconds:
                logger.warning(f"Rate limit exceeded for user {user_id} on {endpoint}. Time since last call: {time_diff}s")
                return False
        
        cache.set(cache_key, current_time, 60)  # Cache for 1 minute
        return True


class RegisterView(APIView):
    """User registration endpoint."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            email = request.data.get("email")
            password = request.data.get("password")

            logger.info(f"Registration attempt for email: {email}")

            if not email or not password:
                return Response(
                    {"error": "Email and password are required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate email format
            if not email or '@' not in email:
                return Response(
                    {"error": "Please provide a valid email address."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if user already exists
            if User.objects.filter(email=email).exists():
                return Response(
                    {"error": "A user with this email already exists."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.create_user(email=email, password=password)
            logger.info(f"User created successfully: {user.email}")
            
            return Response(
                {"message": "User created successfully!", "user_id": user.id}, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred during registration."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(generics.GenericAPIView):
    """User login endpoint."""
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            logger.info(f"Login attempt for email: {request.data.get('email')}")
            serializer = self.get_serializer(data=request.data)
            
            if serializer.is_valid():
                logger.info(f"Login successful for email: {request.data.get('email')}")
                return Response(serializer.validated_data, status=status.HTTP_200_OK)
            else:
                logger.warning(f"Login validation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred during login."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserDetailView(generics.RetrieveAPIView):
    """Get current user details."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListView(APIView):
    """List all users (admin only)."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Access denied. Staff privileges required."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            users = User.objects.all()
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching users: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching users."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClubViewSet(viewsets.ModelViewSet):
    """CRUD operations for clubs."""
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Club.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        logger.info(f"Club created for user: {self.request.user.email}")


class ClubListView(generics.ListAPIView):
    """List all clubs for the authenticated user."""
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Club.objects.filter(user=self.request.user)


class ClubDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific club."""
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Club.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()
        logger.info(f"Club updated: {serializer.instance.name}")

    def perform_destroy(self, instance):
        club_name = instance.name
        instance.delete()
        logger.info(f"Club deleted: {club_name}")


class CreateClubView(APIView):
    """Create a new club."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = ClubSerializer(data=request.data)
            if serializer.is_valid():
                club = serializer.save(user=request.user)
                logger.info(f"Club created: {club.name} for user: {request.user.email}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating club: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while creating the club."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MyClubView(APIView, RateLimitMixin):
    """Get the current user's club."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Add request tracking
            logger.info(f"MyClubView called by user {request.user.email} at {timezone.now()}")
            logger.info(f"Request headers: {dict(request.headers)}")
            
            # Check rate limiting
            if not self.check_rate_limit(request.user.id, "my_club", limit_seconds=3):
                return Response(
                    {
                        "error": "Too many requests. Please wait a few seconds.",
                        "message": "Rate limit exceeded - check frontend for polling issues"
                    }, 
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            club = Club.objects.filter(user=request.user).first()
            if not club:
                logger.warning(f"No club found for user {request.user.email}")
                return Response(
                    {"detail": "No club found for this user."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = ClubSerializer(club)
            logger.info(f"Club data returned for user {request.user.email}: {club.name}")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching user's club: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching your club."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token endpoint with email-based authentication."""
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        try:
            logger.info(f"Token request for email: {request.data.get('email')}")
            
            # Validate content type
            if request.content_type != 'application/json':
                logger.warning(f"Invalid content type: {request.content_type}")
                return Response(
                    {"error": "Content-Type must be application/json"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Test database connection before proceeding
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    logger.info(f"Database connection test in token endpoint: {result}")
            except Exception as db_error:
                logger.error(f"Database connection failed in token endpoint: {str(db_error)}", exc_info=True)
                return Response(
                    {"error": "Database connection failed. Please try again later."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Test User model access
            try:
                user_count = User.objects.count()
                logger.info(f"User model access test: {user_count} users found")
            except Exception as user_error:
                logger.error(f"User model access failed: {str(user_error)}", exc_info=True)
                return Response(
                    {"error": "User database access failed. Please try again later."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            response = super().post(request, *args, **kwargs)
            logger.info(f"Token generated successfully for email: {request.data.get('email')}")
            return response
        except Exception as e:
            logger.error(f"Token generation error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred during token generation."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HealthCheckView(APIView):
    """Health check endpoint."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Test database connection
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            # Test User model access
            user_count = User.objects.count()
            
            return Response({
                "status": "healthy", 
                "message": "Users API is working",
                "database": {
                    "connection": "ok",
                    "user_count": user_count
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}", exc_info=True)
            return Response({
                "status": "unhealthy", 
                "message": "Database connection failed",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        try:
            # Test database connection
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            # Test User model access
            user_count = User.objects.count()
            
            return Response({
                "status": "healthy", 
                "message": "Users API POST is working", 
                "data": request.data,
                "database": {
                    "connection": "ok",
                    "user_count": user_count
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Health check POST failed: {str(e)}", exc_info=True)
            return Response({
                "status": "unhealthy", 
                "message": "Database connection failed",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestTokenEndpointView(APIView):
    """Test endpoint to verify token endpoint is accessible."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response(
            {
                "status": "success",
                "message": "Token endpoint is accessible via GET",
                "method": "GET",
                "headers": dict(request.headers),
                "cors_test": "CORS GET request successful"
            },
            status=status.HTTP_200_OK
        )
    
    def post(self, request):
        return Response(
            {
                "status": "success", 
                "message": "Token endpoint is accessible via POST",
                "method": "POST",
                "data": request.data,
                "content_type": request.content_type,
                "cors_test": "CORS POST request successful"
            },
            status=status.HTTP_200_OK
        )

    def options(self, request):
        """Handle preflight OPTIONS requests for CORS."""
        response = Response(
            {
                "status": "success",
                "message": "CORS preflight request successful",
                "method": "OPTIONS"
            },
            status=status.HTTP_200_OK
        )
        return response


class UploadLogoView(APIView):
    """Upload logo for a club."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            logo_data = request.data.get('logo')
            if not logo_data:
                return Response(
                    {"error": "Logo data is required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Handle base64 data URL
            if logo_data.startswith('data:image/'):
                # Extract the base64 part
                try:
                    # Split on ',' and get the base64 part
                    base64_data = logo_data.split(',')[1]
                    # Decode base64
                    image_data = base64.b64decode(base64_data)
                    
                    # For now, we'll just return the data URL as the logo URL
                    # In production, you might want to upload this to Cloudinary or another service
                    logger.info(f"Logo uploaded for user: {request.user.email}")
                    
                    return Response({
                        "logo_url": logo_data,
                        "message": "Logo uploaded successfully"
                    }, status=status.HTTP_200_OK)
                    
                except Exception as e:
                    logger.error(f"Error processing base64 logo: {str(e)}")
                    return Response(
                        {"error": "Invalid logo format."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Handle regular URL
            elif logo_data.startswith(('http://', 'https://')):
                return Response({
                    "logo_url": logo_data,
                    "message": "Logo URL set successfully"
                }, status=status.HTTP_200_OK)
            
            else:
                return Response(
                    {"error": "Logo must be a valid URL or base64 data URL."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Error uploading logo: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while uploading the logo."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
