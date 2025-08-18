import logging
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

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


class MyClubView(APIView):
    """Get the current user's club."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            club = Club.objects.filter(user=request.user).first()
            if not club:
                return Response(
                    {"detail": "No club found for this user."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = ClubSerializer(club)
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
        return Response(
            {"status": "healthy", "message": "Users API is working"}, 
            status=status.HTTP_200_OK
        )
    
    def post(self, request):
        return Response(
            {
                "status": "healthy", 
                "message": "Users API POST is working", 
                "data": request.data
            }, 
            status=status.HTTP_200_OK
        )


class TestTokenEndpointView(APIView):
    """Test endpoint to verify token endpoint is accessible."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response(
            {
                "status": "success",
                "message": "Token endpoint is accessible via GET",
                "method": "GET",
                "headers": dict(request.headers)
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
                "content_type": request.content_type
            },
            status=status.HTTP_200_OK
        )
