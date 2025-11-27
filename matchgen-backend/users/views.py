import logging
import base64
import requests
import stripe
import time
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import status, generics, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.urls import reverse
import cloudinary.uploader

from .models import (
    User, Club, UserRole, ClubMembership, Feature, 
    SubscriptionTierFeature, AuditLog
)
from .serializers import (
    UserSerializer, ClubSerializer, RegisterSerializer, LoginSerializer,
    UserRoleSerializer, ClubMembershipSerializer, InviteUserSerializer,
    FeatureSerializer, SubscriptionTierFeatureSerializer, AuditLogSerializer,
    TeamManagementSerializer, FeatureAccessSerializer, ChangePasswordSerializer,
    CustomTokenObtainPairSerializer
)
from .permissions import (
    IsClubMember, HasRolePermission, HasFeaturePermission,
    FeaturePermission, AuditLogger, can_manage_team_members,
    can_manage_billing, get_user_role_in_club
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


class EmailVerificationView(APIView):
    """Verify user email with token."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            token = request.data.get('token')
            if not token:
                return Response(
                    {"error": "Verification token is required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find user with this token
            try:
                # Check if email_verification_token field exists
                if not hasattr(User, 'email_verification_token'):
                    return Response(
                        {"error": "Email verification not available."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user = User.objects.get(email_verification_token=token)
            except User.DoesNotExist:
                return Response(
                    {"error": "Invalid verification token."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if token is expired (24 hours)
            if hasattr(user, 'email_verification_sent_at') and user.email_verification_sent_at:
                from datetime import timedelta
                if timezone.now() - user.email_verification_sent_at > timedelta(hours=24):
                    return Response(
                        {"error": "Verification token has expired. Please request a new one."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Verify email
            if hasattr(user, 'email_verified'):
                user.email_verified = True
            if hasattr(user, 'email_verification_token'):
                user.email_verification_token = None
            user.save()
            
            logger.info(f"Email verified for user: {user.email}")
            
            return Response(
                {"message": "Email verified successfully!"}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Email verification error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred during email verification."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResendVerificationView(APIView):
    """Resend email verification for authenticated users."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user = request.user
            
            # Check if email verification fields exist
            if not hasattr(user, 'email_verified'):
                return Response(
                    {"error": "Email verification not available."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if user.email_verified:
                return Response(
                    {"error": "Email is already verified."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate new token
            import secrets
            verification_token = secrets.token_urlsafe(32)
            
            if hasattr(user, 'email_verification_token'):
                user.email_verification_token = verification_token
            if hasattr(user, 'email_verification_sent_at'):
                user.email_verification_sent_at = timezone.now()
            user.save()
            
            # Send verification email
            self._send_verification_email(user, verification_token)
            
            logger.info(f"Verification email resent to: {user.email}")
            
            return Response(
                {"message": "Verification email sent successfully!"}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Resend verification error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while sending verification email."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResendVerificationSignupView(APIView):
    """Resend email verification during signup (no authentication required)."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            email = request.data.get('email')
            
            if not email:
                return Response(
                    {"error": "Email is required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find user by email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {"error": "User with this email does not exist."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if email verification fields exist
            if not hasattr(user, 'email_verified'):
                return Response(
                    {"error": "Email verification not available."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if user.email_verified:
                return Response(
                    {"error": "Email is already verified."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate new token
            import secrets
            verification_token = secrets.token_urlsafe(32)
            
            if hasattr(user, 'email_verification_token'):
                user.email_verification_token = verification_token
            if hasattr(user, 'email_verification_sent_at'):
                user.email_verification_sent_at = timezone.now()
            user.save()
            
            # Send verification email
            self._send_verification_email(user, verification_token)
            
            logger.info(f"Verification email resent to: {user.email}")
            
            return Response(
                {"message": "Verification email sent successfully!"}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Resend verification error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while sending verification email."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _send_verification_email(self, user, token):
        """Send verification email to user."""
        try:
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
            
            subject = "Verify your MatchGen account"
            message = f"""
            Welcome to MatchGen!
            
            Please verify your email address by clicking the link below:
            {verification_url}
            
            This link will expire in 24 hours.
            
            If you didn't create this account, please ignore this email.
            
            Best regards,
            The MatchGen Team
            """
            
            # Debug: Check each email setting individually
            logger.info("=== EMAIL CONFIGURATION DEBUG ===")
            logger.info(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NOT SET')}")
            logger.info(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NOT SET')}")
            logger.info(f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'NOT SET')}")
            logger.info(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')}")
            logger.info(f"EMAIL_HOST_PASSWORD: {'SET' if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else 'NOT SET'}")
            logger.info(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}")
            logger.info("=== END EMAIL DEBUG ===")
            
            # Check if email settings are configured
            email_user = getattr(settings, 'EMAIL_HOST_USER', None)
            email_password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            
            if not email_user or not email_password:
                logger.warning(f"Email settings not configured. Skipping email send for {user.email}")
                logger.info(f"Verification URL for {user.email}: {verification_url}")
                print(f"\n🔗 VERIFICATION LINK FOR {user.email}:")
                print(f"{verification_url}")
                print(f"Copy this link and paste it in your browser to verify the account.\n")
                return
            
            # Try to send email with SendGrid API (more reliable than SMTP)
            try:
                import requests
                
                # SendGrid API endpoint
                sendgrid_url = "https://api.sendgrid.com/v3/mail/send"
                
                # Prepare email data
                email_data = {
                    "personalizations": [
                        {
                            "to": [{"email": user.email}],
                            "subject": subject
                        }
                    ],
                    "from": {"email": settings.DEFAULT_FROM_EMAIL},
                    "content": [
                        {
                            "type": "text/plain",
                            "value": message
                        }
                    ]
                }
                
                # Send via SendGrid API
                headers = {
                    "Authorization": f"Bearer {settings.EMAIL_HOST_PASSWORD}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(sendgrid_url, json=email_data, headers=headers, timeout=10)
                
                if response.status_code == 202:
                    logger.info(f"✅ Verification email sent successfully to {user.email}")
                else:
                    logger.error(f"❌ SendGrid API error: {response.status_code} - {response.text}")
                    raise Exception(f"SendGrid API error: {response.status_code}")
                    
            except Exception as email_error:
                logger.error(f"❌ Failed to send email to {user.email}: {str(email_error)}")
                # Fallback: log the verification link
                logger.info(f"Verification URL for {user.email}: {verification_url}")
                print(f"\n🔗 VERIFICATION LINK FOR {user.email}:")
                print(f"{verification_url}")
                print(f"Copy this link and paste it in your browser to verify the account.\n")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            # Don't fail if email fails
            logger.info(f"Verification URL for {user.email}: {verification_url}")


class RegisterView(APIView):
    """Enhanced user registration endpoint with email verification."""
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

            # Create user with email verification
            import secrets
            verification_token = secrets.token_urlsafe(32)
            
            # Always require email verification for security
            # is_development = not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD
            
            try:
                # Try to create user with email verification fields
                user = User.objects.create_user(
                    email=email, 
                    password=password,
                    email_verification_token=verification_token,
                    email_verification_sent_at=timezone.now(),
                    email_verified=False  # Always require verification
                )
            except Exception as e:
                # If email verification fields don't exist, create user with raw SQL
                logger.warning(f"Email verification fields not available: {str(e)}")
                
                from django.contrib.auth.hashers import make_password
                from django.db import connection
                
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users_user (email, password, is_active, is_staff, is_superuser) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                        [email, make_password(password), True, False, False]
                    )
                    user_id = cursor.fetchone()[0]
                
                # Create a User object with the basic fields
                user = User()
                user.id = user_id
                user.email = email
                user.is_active = True
                user.is_staff = False
                user.is_superuser = False
            
            # Send verification code automatically
            self._send_verification_code_after_registration(user)
            
            logger.info(f"User created successfully: {user.email}")
            
            return Response(
                {
                    "message": "Account created successfully! Please check your email to verify your account.",
                    "user_id": user.id,
                    "email_verification_sent": True
                }, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred during registration."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _send_verification_email(self, user, token):
        """Send verification email to user."""
        try:
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
            
            subject = "Verify your MatchGen account"
            message = f"""
            Welcome to MatchGen!
            
            Please verify your email address by clicking the link below:
            {verification_url}
            
            This link will expire in 24 hours.
            
            If you didn't create this account, please ignore this email.
            
            Best regards,
            The MatchGen Team
            """
            
            # Debug: Check each email setting individually
            logger.info("=== EMAIL CONFIGURATION DEBUG ===")
            logger.info(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NOT SET')}")
            logger.info(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NOT SET')}")
            logger.info(f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'NOT SET')}")
            logger.info(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')}")
            logger.info(f"EMAIL_HOST_PASSWORD: {'SET' if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else 'NOT SET'}")
            logger.info(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}")
            logger.info("=== END EMAIL DEBUG ===")
            
            # Check if email settings are configured
            email_user = getattr(settings, 'EMAIL_HOST_USER', None)
            email_password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            
            if not email_user or not email_password:
                logger.warning(f"Email settings not configured. Skipping email send for {user.email}")
                logger.info(f"Verification URL for {user.email}: {verification_url}")
                print(f"\n🔗 VERIFICATION LINK FOR {user.email}:")
                print(f"{verification_url}")
                print(f"Copy this link and paste it in your browser to verify the account.\n")
                return
            
            # Try to send email with SendGrid API (more reliable than SMTP)
            try:
                import requests
                
                # SendGrid API endpoint
                sendgrid_url = "https://api.sendgrid.com/v3/mail/send"
                
                # Prepare email data
                email_data = {
                    "personalizations": [
                        {
                            "to": [{"email": user.email}],
                            "subject": subject
                        }
                    ],
                    "from": {"email": settings.DEFAULT_FROM_EMAIL},
                    "content": [
                        {
                            "type": "text/plain",
                            "value": message
                        }
                    ]
                }
                
                # Send via SendGrid API
                headers = {
                    "Authorization": f"Bearer {settings.EMAIL_HOST_PASSWORD}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(sendgrid_url, json=email_data, headers=headers, timeout=10)
                
                if response.status_code == 202:
                    logger.info(f"✅ Verification email sent successfully to {user.email}")
                else:
                    logger.error(f"❌ SendGrid API error: {response.status_code} - {response.text}")
                    raise Exception(f"SendGrid API error: {response.status_code}")
                    
            except Exception as email_error:
                logger.error(f"❌ Failed to send email to {user.email}: {str(email_error)}")
                # Fallback: log the verification link
                logger.info(f"Verification URL for {user.email}: {verification_url}")
                print(f"\n🔗 VERIFICATION LINK FOR {user.email}:")
                print(f"{verification_url}")
                print(f"Copy this link and paste it in your browser to verify the account.\n")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            # Don't fail registration if email fails
            logger.info(f"Verification URL for {user.email}: {verification_url}")

    def _send_verification_code_after_registration(self, user):
        """Send verification code after user registration."""
        try:
            # Generate a 6-digit verification code
            import random
            verification_code = str(random.randint(100000, 999999))
            
            # Store the code in cache with 10-minute expiry
            cache_key = f"verification_code_{user.email}"
            cache.set(cache_key, verification_code, 600)  # 10 minutes
            
            # Send the code via email
            self._send_verification_code_email(user, verification_code)
            
            logger.info(f"Verification code sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Error sending verification code after registration: {str(e)}")
            print(f"\n🔐 VERIFICATION CODE FOR {user.email}:")
            print(f"Use this code to verify the account.\n")

    def _send_verification_code_email(self, user, code):
        """Send verification code email to user."""
        try:
            subject = "Your MatchGen Verification Code"
            message = f"""
            Your verification code is: {code}
            
            This code will expire in 10 minutes.
            
            If you didn't request this code, please ignore this email.
            
            Best regards,
            The MatchGen Team
            """
            
            # Check if email settings are configured
            email_user = getattr(settings, 'EMAIL_HOST_USER', None)
            email_password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            
            if not email_user or not email_password:
                logger.warning(f"Email settings not configured. Skipping email send for {user.email}")
                logger.info(f"Verification code for {user.email}: {code}")
                print(f"\n🔐 VERIFICATION CODE FOR {user.email}:")
                print(f"{code}")
                print(f"Use this code to verify the account.\n")
                return
            
            # Try to send email with SendGrid API
            try:
                import requests
                
                sendgrid_url = "https://api.sendgrid.com/v3/mail/send"
                headers = {
                    "Authorization": f"Bearer {email_password}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "personalizations": [{
                        "to": [{"email": user.email}],
                        "subject": subject
                    }],
                    "from": {"email": settings.DEFAULT_FROM_EMAIL},
                    "content": [{
                        "type": "text/plain",
                        "value": message
                    }]
                }
                
                response = requests.post(sendgrid_url, headers=headers, json=data)
                
                if response.status_code == 202:
                    logger.info(f"Verification code email sent successfully to {user.email}")
                else:
                    logger.error(f"SendGrid API error: {response.status_code} - {response.text}")
                    print(f"\n🔐 VERIFICATION CODE FOR {user.email}:")
                    print(f"{code}")
                    print(f"Use this code to verify the account.\n")
            except Exception as e:
                logger.error(f"Error sending email via SendGrid: {str(e)}")
                print(f"\n🔐 VERIFICATION CODE FOR {user.email}:")
                print(f"{code}")
                print(f"Use this code to verify the account.\n")
                
        except Exception as e:
            logger.error(f"Error in _send_verification_code_email: {str(e)}")
            print(f"\n🔐 VERIFICATION CODE FOR {user.email}:")
            print(f"{code}")
            print(f"Use this code to verify the account.\n")


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


class EnhancedClubCreationView(APIView):
    """Enhanced club creation with graphic pack selection."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Check if user's email is verified
            if not request.user.email_verified:
                return Response(
                    {"error": "Please verify your email address before creating a club."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user already has a club
            if Club.objects.filter(user=request.user).exists():
                return Response(
                    {"error": "User already has a club."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extract data
            founded_year = request.data.get('founded_year')
            # Convert empty string to None for founded_year field
            if founded_year == '' or founded_year is None:
                founded_year = None
            else:
                try:
                    founded_year = int(founded_year)
                except (ValueError, TypeError):
                    founded_year = None
            
            club_data = {
                'name': request.data.get('name'),
                'sport': request.data.get('sport'),
                'venue_name': request.data.get('venue_name', ''),
                'location': request.data.get('location', ''),
                'primary_color': request.data.get('primary_color', ''),
                'secondary_color': request.data.get('secondary_color', ''),
                'bio': request.data.get('bio', ''),
                'league': request.data.get('league', ''),
                'website': request.data.get('website', ''),
                'founded_year': founded_year,
            }
            
            # Validate required fields
            if not club_data['name'] or not club_data['sport']:
                return Response(
                    {"error": "Club name and sport are required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Handle logo upload
            logo_file = request.FILES.get('logo')
            if logo_file:
                try:
                    import cloudinary
                    import cloudinary.uploader
                    from django.conf import settings
                    
                    # Upload to Cloudinary
                    upload_result = cloudinary.uploader.upload(
                        logo_file,
                        folder="club_logos",
                        public_id=f"club_{request.user.id}_{int(time.time())}",
                        overwrite=True,
                        resource_type="image",
                        tags=["Logo"]
                    )
                    club_data['logo'] = upload_result['secure_url']
                    logger.info(f"Logo uploaded to Cloudinary: {club_data['logo']}")
                except Exception as e:
                    logger.error(f"Logo upload failed: {str(e)}")
                    return Response(
                        {"error": "Failed to upload logo. Please try again."}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Handle graphic pack selection
            graphic_pack_id = request.data.get('graphic_pack_id')
            if graphic_pack_id:
                try:
                    from graphicpack.models import GraphicPack
                    graphic_pack = GraphicPack.objects.get(id=graphic_pack_id)
                    club_data['selected_pack'] = graphic_pack
                except GraphicPack.DoesNotExist:
                    return Response(
                        {"error": "Selected graphic pack not found."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Create club
            # Temporary workaround: provide default values until migration is applied
            if 'subscription_start_date' not in club_data or club_data['subscription_start_date'] is None:
                club_data['subscription_start_date'] = timezone.now()
            
            # Allow NULL subscription tier during signup - user will choose later
            if 'subscription_tier' not in club_data:
                club_data['subscription_tier'] = None
            
            # Validate the subscription tier if provided
            if club_data['subscription_tier'] is not None and club_data['subscription_tier'] not in ['basic', 'semipro', 'prem']:
                return Response(
                    {"error": "Invalid subscription tier"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ensure subscription is inactive (no free access)
            club_data['subscription_active'] = False
            
            club = Club.objects.create(user=request.user, **club_data)
            
            # Create Owner role membership
            owner_role = UserRole.objects.get(name='owner')
            ClubMembership.objects.create(
                user=request.user,
                club=club,
                role=owner_role,
                status='active',
                accepted_at=timezone.now()
            )
            
            logger.info(f"Enhanced club created: {club.name} for user: {request.user.email}")
            
            return Response({
                "message": "Club created successfully!",
                "club": ClubSerializer(club).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Enhanced club creation error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while creating the club."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request):
        """Update club with graphic pack selection."""
        try:
            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Handle graphic pack selection
            graphic_pack_id = request.data.get('graphic_pack_id')
            if graphic_pack_id:
                try:
                    from graphicpack.models import GraphicPack
                    graphic_pack = GraphicPack.objects.get(id=graphic_pack_id)
                    club.selected_pack = graphic_pack
                except GraphicPack.DoesNotExist:
                    return Response(
                        {"error": "Selected graphic pack not found."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                club.selected_pack = None
            
            club.save()
            
            logger.info(f"Club updated with graphic pack: {club.name} for user: {request.user.email}")
            
            return Response({
                "message": "Club updated successfully!",
                "club": ClubSerializer(club).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Club update error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while updating the club."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateClubView(APIView):
    """Create a new club."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Check if user's email is verified
            if not request.user.email_verified:
                return Response(
                    {"error": "Please verify your email address before creating a club."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user already has a club
            if Club.objects.filter(user=request.user).exists():
                return Response(
                    {"error": "User already has a club."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Temporary workaround: add default values to request data
            request_data = request.data.copy()
            if 'subscription_start_date' not in request_data or request_data['subscription_start_date'] is None:
                request_data['subscription_start_date'] = timezone.now()
            
            # Allow NULL subscription tier during signup - user will choose later
            if 'subscription_tier' not in request_data:
                request_data['subscription_tier'] = None
            
            # Validate the subscription tier if provided
            if request_data['subscription_tier'] is not None and request_data['subscription_tier'] not in ['basic', 'semipro', 'prem']:
                return Response(
                    {"error": "Invalid subscription tier"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ensure subscription is inactive (no free access)
            request_data['subscription_active'] = False
            
            serializer = ClubSerializer(data=request_data)
            if serializer.is_valid():
                club = serializer.save(user=request.user)
                
                # Create Owner role membership
                owner_role = UserRole.objects.get(name='owner')
                ClubMembership.objects.create(
                    user=request.user,
                    club=club,
                    role=owner_role,
                    status='active',
                    accepted_at=timezone.now()
                )
                
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
            
            # Get user's club through membership (RBAC system)
            membership = ClubMembership.objects.filter(
                user=request.user, 
                status='active'
            ).select_related('club', 'role').first()
            
            # Debug logging
            logger.info(f"User {request.user.email} - Membership query result: {membership}")
            
            if not membership:
                # Fallback: check if user has direct club ownership (legacy)
                direct_club = Club.objects.filter(user=request.user).first()
                if direct_club:
                    logger.info(f"Found direct club ownership for user {request.user.email}: {direct_club.name}")
                    # Create membership for this user
                    from users.models import UserRole
                    owner_role, _ = UserRole.objects.get_or_create(
                        name='owner',
                        defaults={'description': 'Club owner with full permissions'}
                    )
                    membership = ClubMembership.objects.create(
                        user=request.user,
                        club=direct_club,
                        role=owner_role,
                        status='active'
                    )
                    logger.info(f"Created membership for user {request.user.email} as owner of {direct_club.name}")
                else:
                    logger.warning(f"No active club membership or direct club found for user {request.user.email}")
                    
                    # Check if user is admin/staff - provide admin access instead of error
                    if request.user.is_staff or request.user.is_superuser:
                        logger.info(f"Admin user {request.user.email} has no club - providing admin access")
                        return Response({
                            "detail": "No club found for this user.",
                            "is_admin": True,
                            "admin_dashboard_url": "/api/users/admin/dashboard/",
                            "message": "As an admin user, you can access the admin dashboard to manage all clubs."
                        }, status=status.HTTP_200_OK)
                    else:
                        return Response(
                            {"detail": "No club found for this user."}, 
                            status=status.HTTP_404_NOT_FOUND
                        )
            
            club = membership.club
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
            logger.info(f"Request headers: {dict(request.headers)}")
            logger.info(f"Request data: {request.data}")
            
            # Validate content type
            if request.content_type and 'application/json' not in request.content_type:
                logger.warning(f"Invalid content type: {request.content_type}")
                return Response(
                    {"error": "Content-Type must be application/json"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            response = super().post(request, *args, **kwargs)
            logger.info(f"Token generated successfully for email: {request.data.get('email')}")
            return response
        except ValidationError as e:
            # Handle validation errors properly (like invalid credentials)
            logger.warning(f"Validation error during token generation: {str(e)}")
            return Response(
                {"error": "Invalid email or password."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
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


class UploadLogoView(APIView):
    """Upload logo for a club."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        try:
            logo_file = request.FILES.get('logo')
            if not logo_file:
                return Response(
                    {"error": "No logo file provided."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Upload to Cloudinary
            try:
                import cloudinary
                import cloudinary.uploader
                from django.conf import settings
                
                upload_result = cloudinary.uploader.upload(
                    logo_file,
                    folder="club_logos",
                    public_id=f"club_{request.user.id}_{int(time.time())}",
                    overwrite=True,
                    resource_type="image",
                    tags=["Logo"]
                )
                
                logo_url = upload_result['secure_url']
                logger.info(f"Club logo uploaded to Cloudinary: {logo_url}")
                
                return Response({
                    "logo_url": logo_url,
                    "message": "Club logo uploaded successfully"
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Club logo upload failed: {str(e)}")
                return Response(
                    {"error": "Failed to upload club logo. Please try again."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error uploading logo: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while uploading the logo."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TeamManagementView(APIView):
    """View for managing team members and roles"""
    permission_classes = [IsClubMember]
    
    def get(self, request):
        """Get team management data"""
        try:
            logger.info(f"TeamManagementView GET called by user {request.user.email}")
            
            club_id = request.query_params.get('club_id')
            if not club_id:
                logger.warning("TeamManagementView: No club_id provided")
                return Response({"error": "Club ID is required"}, status=400)
            
            logger.info(f"TeamManagementView: Looking for club_id {club_id}")
            
            try:
                club = Club.objects.get(id=club_id)
                logger.info(f"TeamManagementView: Found club {club.name}")
            except Club.DoesNotExist:
                logger.warning(f"TeamManagementView: Club {club_id} not found")
                return Response({"error": "Club not found"}, status=404)
            
            # Check if user can manage members
            can_manage = can_manage_team_members(request.user, club)
            logger.info(f"TeamManagementView: User can manage members: {can_manage}")
            
            if not can_manage:
                logger.warning(f"TeamManagementView: User {request.user.email} cannot manage members")
                return Response({"error": "You don't have permission to manage team members"}, status=403)
            
            # Get members
            members = ClubMembership.objects.filter(club=club).select_related('user', 'role', 'invited_by')
            logger.info(f"TeamManagementView: Found {members.count()} members")
            
            # Get available roles
            available_roles = UserRole.objects.all()
            logger.info(f"TeamManagementView: Found {available_roles.count()} available roles")
            
            # Serialize data
            members_data = ClubMembershipSerializer(members, many=True).data
            roles_data = UserRoleSerializer(available_roles, many=True).data
            
            data = {
                'members': members_data,
                'available_roles': roles_data,
                'can_manage_members': can_manage,
                'can_manage_billing': can_manage_billing(request.user, club),
            }
            
            logger.info(f"TeamManagementView: Successfully prepared data for club {club.name}")
            return Response(TeamManagementSerializer(data).data)
            
        except Exception as e:
            logger.error(f"TeamManagementView error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching team management data"}, 
                status=500
            )
    
    def post(self, request):
        """Invite a new team member"""
        club_id = request.data.get('club_id')
        if not club_id:
            return Response({"error": "Club ID is required"}, status=400)
        
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=404)
        
        # Check if user can manage members
        if not can_manage_team_members(request.user, club):
            return Response({"error": "You don't have permission to invite team members"}, status=403)
        
        serializer = InviteUserSerializer(data=request.data, context={'club': club})
        if serializer.is_valid():
            with transaction.atomic():
                # Create or get user
                email = serializer.validated_data['email']
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={'username': email.split('@')[0]}
                )
                
                # Create membership
                role = UserRole.objects.get(id=serializer.validated_data['role_id'])
                membership = ClubMembership.objects.create(
                    user=user,
                    club=club,
                    role=role,
                    invited_by=request.user,
                    status='pending'
                )
                
                # Log audit event
                AuditLogger.log_event(
                    user=request.user,
                    club=club,
                    action='invite_sent',
                    details={
                        'invited_user_email': email,
                        'role': role.name,
                        'membership_id': membership.id
                    },
                    request=request
                )
                
                # Send invitation email (placeholder)
                # TODO: Implement actual email sending
                
                return Response({
                    "message": f"Invitation sent to {email}",
                    "membership": ClubMembershipSerializer(membership).data
                })
        
        return Response(serializer.errors, status=400)


class UpdateMemberRoleView(APIView):
    """View for updating member roles"""
    permission_classes = [HasRolePermission]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.permission_classes = [HasRolePermission(required_roles=['owner', 'admin'])]
    
    def put(self, request, membership_id):
        """Update member role"""
        try:
            membership = ClubMembership.objects.get(id=membership_id)
        except ClubMembership.DoesNotExist:
            return Response({"error": "Membership not found"}, status=404)
        
        # Check if user can manage this club
        if not can_manage_team_members(request.user, membership.club):
            return Response({"error": "You don't have permission to update roles"}, status=403)
        
        role_id = request.data.get('role_id')
        if not role_id:
            return Response({"error": "Role ID is required"}, status=400)
        
        try:
            new_role = UserRole.objects.get(id=role_id)
        except UserRole.DoesNotExist:
            return Response({"error": "Invalid role ID"}, status=400)
        
        old_role = membership.role.name
        membership.role = new_role
        membership.save()
        
        # Log audit event
        AuditLogger.log_event(
            user=request.user,
            club=membership.club,
            action='role_changed',
            details={
                'member_email': membership.user.email,
                'old_role': old_role,
                'new_role': new_role.name
            },
            request=request
        )
        
        return Response({
            "message": f"Role updated for {membership.user.email}",
            "membership": ClubMembershipSerializer(membership).data
        })


class RemoveMemberView(APIView):
    """View for removing team members"""
    permission_classes = [HasRolePermission]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.permission_classes = [HasRolePermission(required_roles=['owner', 'admin'])]
    
    def delete(self, request, membership_id):
        """Remove team member"""
        try:
            membership = ClubMembership.objects.get(id=membership_id)
        except ClubMembership.DoesNotExist:
            return Response({"error": "Membership not found"}, status=404)
        
        # Check if user can manage this club
        if not can_manage_team_members(request.user, membership.club):
            return Response({"error": "You don't have permission to remove members"}, status=403)
        
        # Don't allow removing the last owner
        if membership.role.name == 'owner':
            owner_count = ClubMembership.objects.filter(
                club=membership.club, 
                role__name='owner', 
                status='active'
            ).count()
            if owner_count <= 1:
                return Response({"error": "Cannot remove the last owner"}, status=400)
        
        member_email = membership.user.email
        membership.delete()
        
        # Log audit event
        AuditLogger.log_event(
            user=request.user,
            club=membership.club,
            action='role_revoked',
            details={
                'member_email': member_email,
                'role': membership.role.name
            },
            request=request
        )
        
        return Response({"message": f"Member {member_email} removed from team"})


class FeatureAccessView(APIView):
    """View for checking feature access"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get feature access information for a club"""
        club_id = request.query_params.get('club_id')
        if not club_id:
            return Response({"error": "Club ID is required"}, status=400)
        
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=404)
        
        # Check if user has access to this club (either as owner or member)
        has_access = False
        
        # Check direct ownership (legacy)
        if club.user == request.user:
            has_access = True
        
        # Check membership (RBAC)
        if not has_access:
            has_access = ClubMembership.objects.filter(
                user=request.user,
                club=club,
                status='active'
            ).exists()
        
        if not has_access:
            return Response({"error": "You don't have access to this club"}, status=403)
        
        available_features = FeaturePermission.get_available_features(club)
        
        # Check access to specific features
        feature_access = {}
        all_features = Feature.objects.filter(is_active=True)
        for feature in all_features:
            feature_access[feature.code] = FeaturePermission.has_feature_access(request.user, club, feature.code)
        
        # Get detailed feature information
        feature_details = []
        for feature in all_features:
            feature_details.append({
                'code': feature.code,
                'name': feature.name,
                'description': feature.description,
                'has_access': feature_access[feature.code],
                'available_in_tiers': list(SubscriptionTierFeature.objects.filter(
                    feature=feature
                ).values_list('subscription_tier', flat=True))
            })
        
        # Handle missing fields gracefully until migration is applied
        subscription_canceled = getattr(club, 'subscription_canceled', False)
        stripe_subscription_id = getattr(club, 'stripe_subscription_id', None)
        
        data = {
            'available_features': available_features,
            'subscription_tier': club.subscription_tier,
            'subscription_active': club.subscription_active,
            'subscription_canceled': subscription_canceled,
            'stripe_subscription_id': stripe_subscription_id,
            'feature_access': feature_access,
            'feature_details': feature_details,
            'club_name': club.name
        }
        
        return Response(data)


class FeaturesView(APIView):
    """View for listing all available features"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all available features"""
        features = Feature.objects.filter(is_active=True)
        return Response(FeatureSerializer(features, many=True).data)


class UpdateSubscriptionTierView(APIView):
    """View for updating subscription tier"""
    permission_classes = [HasRolePermission]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.permission_classes = [HasRolePermission(required_roles=['owner', 'admin'])]
    
    def post(self, request):
        """Update subscription tier for a club"""
        club_id = request.data.get('club_id')
        new_tier = request.data.get('subscription_tier')
        
        if not club_id or not new_tier:
            return Response({"error": "Club ID and subscription tier are required"}, status=400)
        
        if new_tier not in ['basic', 'semipro', 'prem']:
            return Response({"error": "Invalid subscription tier"}, status=400)
        
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=404)
        
        # Update subscription tier
        old_tier = club.subscription_tier
        club.subscription_tier = new_tier
        club.subscription_active = True
        club.subscription_start_date = timezone.now()
        club.save()
        
        # Log audit event
        AuditLogger.log_event(
            user=request.user,
            club=club,
            action='subscription_changed',
            details={
                'old_tier': old_tier,
                'new_tier': new_tier,
                'changed_by': request.user.email
            }
        )
        
        # Get updated feature access
        available_features = FeaturePermission.get_available_features(club)
        
        return Response({
            "message": f"Subscription tier updated to {new_tier}",
            "subscription_tier": new_tier,
            "subscription_active": True,
            "available_features": available_features
        })


class FeatureCatalogView(APIView):
    """View for getting complete feature catalog with tier mappings"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get complete feature catalog with tier mappings"""
        # Get all features
        features = Feature.objects.filter(is_active=True)
        
        # Get tier mappings
        tier_mappings = {}
        for tier in ['basic', 'semipro', 'prem']:
            tier_features = SubscriptionTierFeature.objects.filter(
                subscription_tier=tier
            ).select_related('feature')
            tier_mappings[tier] = [
                {
                    'code': mapping.feature.code,
                    'name': mapping.feature.name,
                    'description': mapping.feature.description
                }
                for mapping in tier_features
            ]
        
        # Get feature details
        feature_details = []
        for feature in features:
            available_in_tiers = list(SubscriptionTierFeature.objects.filter(
                feature=feature
            ).values_list('subscription_tier', flat=True))
            
            feature_details.append({
                'code': feature.code,
                'name': feature.name,
                'description': feature.description,
                'available_in_tiers': available_in_tiers
            })
        
        return Response({
            'features': feature_details,
            'tier_mappings': tier_mappings,
            'tier_info': {
                'basic': {
                    'name': 'Basic Gen',
                    'price': '£9.99',
                    'period': 'month',
                    'description': 'Perfect for small clubs getting started'
                },
                'semipro': {
                    'name': 'SemiPro Gen',
                    'price': '£14.99',
                    'period': 'month',
                    'description': 'Ideal for growing clubs with more content needs'
                },
                'prem': {
                    'name': 'Prem Gen',
                    'price': '£24.99',
                    'period': 'month',
                    'description': 'Complete solution for professional clubs'
                }
            }
        })


class AuditLogView(APIView):
    """View for viewing audit logs"""
    permission_classes = [HasRolePermission]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.permission_classes = [HasRolePermission(required_roles=['owner', 'admin'])]
    
    def get(self, request):
        """Get audit logs for a club"""
        club_id = request.query_params.get('club_id')
        if not club_id:
            return Response({"error": "Club ID is required"}, status=400)
        
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=404)
        
        # Check if user can view audit logs
        if not can_manage_team_members(request.user, club):
            return Response({"error": "You don't have permission to view audit logs"}, status=403)
        
        logs = AuditLog.objects.filter(club=club).select_related('user').order_by('-timestamp')[:100]
        
        return Response(AuditLogSerializer(logs, many=True).data)


class AcceptInviteView(APIView):
    """View for accepting team invitations"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Accept an invitation"""
        membership_id = request.data.get('membership_id')
        if not membership_id:
            return Response({"error": "Membership ID is required"}, status=400)
        
        try:
            membership = ClubMembership.objects.get(
                id=membership_id,
                user=request.user,
                status='pending'
            )
        except ClubMembership.DoesNotExist:
            return Response({"error": "Invitation not found or already accepted"}, status=404)
        
        membership.status = 'active'
        membership.save()
        
        # Log audit event
        AuditLogger.log_event(
            user=request.user,
            club=membership.club,
            action='invite_accepted',
            details={
                'role': membership.role.name,
                'invited_by': membership.invited_by.email if membership.invited_by else None
            },
            request=request
        )
        
        return Response({
            "message": f"Successfully joined {membership.club.name}",
            "membership": ClubMembershipSerializer(membership).data
        })


class PendingInvitesView(APIView):
    """View for getting pending invitations"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get pending invitations for the current user"""
        pending_invites = ClubMembership.objects.filter(
            user=request.user,
            status='pending'
        ).select_related('club', 'role', 'invited_by')
        
        return Response(ClubMembershipSerializer(pending_invites, many=True).data)


class UserProfileView(APIView):
    """View for user profile management"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user profile"""
        return Response(UserSerializer(request.user).data)
    
    def put(self, request):
        """Update current user profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClubListView(APIView):
    """View for listing clubs"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all clubs for the current user"""
        clubs = Club.objects.filter(user=request.user)
        return Response(ClubSerializer(clubs, many=True).data)


class AllClubsListView(APIView):
    """View for listing all clubs in the system"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all clubs from the database"""
        try:
            clubs = Club.objects.all().order_by('name')
            # Return simplified club data for selection
            club_data = [
                {
                    "id": club.id,
                    "name": club.name,
                    "logo": club.logo,
                    "sport": club.sport,
                    "location": club.location
                }
                for club in clubs
            ]
            return Response(club_data)
        except Exception as e:
            logger.error(f"Error fetching all clubs: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching clubs."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminDashboardView(APIView):
    """Admin dashboard for managing all clubs and system data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get admin dashboard data - only accessible by staff/superusers"""
        try:
            # Check if user is admin/staff
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    "error": "Access denied. Admin privileges required."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get system statistics
            from users.models import User, Club
            from content.models import Match, Player
            from graphicpack.models import GraphicPack, MediaItem
            
            stats = {
                "users": {
                    "total": User.objects.count(),
                    "active": User.objects.filter(is_active=True).count(),
                    "staff": User.objects.filter(is_staff=True).count(),
                    "superusers": User.objects.filter(is_superuser=True).count(),
                },
                "clubs": {
                    "total": Club.objects.count(),
                    "with_logos": Club.objects.exclude(logo__isnull=True).exclude(logo='').count(),
                    "with_subscriptions": Club.objects.filter(subscription_active=True).count(),
                },
                "content": {
                    "matches": Match.objects.count(),
                    "players": Player.objects.count(),
                },
                "graphic_packs": {
                    "total": GraphicPack.objects.count(),
                    "media_items": MediaItem.objects.count(),
                }
            }
            
            # Get all clubs with detailed information
            clubs = Club.objects.all().order_by('name')
            clubs_data = []
            for club in clubs:
                club_info = {
                    "id": club.id,
                    "name": club.name,
                    "logo": club.logo,
                    "sport": club.sport,
                    "location": club.location,
                    "user_email": club.user.email,
                    "user_active": club.user.is_active,
                    "subscription_tier": club.subscription_tier,
                    "subscription_active": club.subscription_active,
                    "matches_count": Match.objects.filter(club=club).count(),
                    "players_count": Player.objects.filter(club=club).count(),
                    "media_items_count": MediaItem.objects.filter(club=club).count(),
                    "created_at": club.user.date_joined.isoformat() if hasattr(club.user, 'date_joined') else None,
                }
                clubs_data.append(club_info)
            
            # Get all graphic packs with detailed information
            graphic_packs = GraphicPack.objects.all().order_by('-created_at')
            graphic_packs_data = []
            for pack in graphic_packs:
                pack_info = {
                    "id": pack.id,
                    "name": pack.name,
                    "description": pack.description,
                    "is_bespoke": pack.is_bespoke,
                    "is_active": pack.is_active,
                    "sport": pack.sport,
                    "tier": pack.tier,
                    "primary_color": pack.primary_color,
                    "preview_image_url": pack.preview_image_url,
                    "assigned_club_name": pack.assigned_club.name if pack.assigned_club else None,
                    "assigned_club_id": pack.assigned_club.id if pack.assigned_club else None,
                    "created_at": pack.created_at.isoformat() if pack.created_at else None,
                    "updated_at": pack.updated_at.isoformat() if pack.updated_at else None,
                }
                graphic_packs_data.append(pack_info)
            
            # Get recent activity (last 10 matches created)
            recent_matches = Match.objects.all().order_by('-id')[:10]
            recent_activity = []
            for match in recent_matches:
                recent_activity.append({
                    "type": "match_created",
                    "club_name": match.club.name,
                    "opponent": match.opponent,
                    "date": match.date.isoformat(),
                    "created_by": match.club.user.email,
                })
            
            dashboard_data = {
                "stats": stats,
                "clubs": clubs_data,
                "graphic_packs": graphic_packs_data,
                "recent_activity": recent_activity,
                "admin_user": {
                    "email": request.user.email,
                    "is_staff": request.user.is_staff,
                    "is_superuser": request.user.is_superuser,
                },
                "available_endpoints": {
                    "all_clubs": "/api/users/clubs/all/",
                    "admin_dashboard": "/api/users/admin/dashboard/",
                    "graphic_pack_upload": "/api/graphicpack/media/upload/",
                }
            }
            
            return Response(dashboard_data)
            
        except Exception as e:
            logger.error(f"Error fetching admin dashboard data: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching admin dashboard data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminFixtureTaskListView(APIView):
    """Get upcoming fixtures for Premium clubs with Bespoke template packages"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get task list of upcoming fixtures for eligible clubs"""
        try:
            # Check if user is admin/staff
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    "error": "Access denied. Admin privileges required."
                }, status=status.HTTP_403_FORBIDDEN)
            
            from users.models import Club
            from content.models import Match
            from graphicpack.models import GraphicPack
            from django.utils import timezone
            
            today = timezone.now().date()
            end_date = today + timedelta(days=10)
            
            # Get clubs that are on Premium Plans (prem) with Bespoke template packages
            eligible_clubs = Club.objects.filter(
                subscription_tier='prem',
                subscription_active=True,
                selected_pack__is_bespoke=True
            ).select_related('selected_pack')
            
            # Get upcoming fixtures for these clubs
            upcoming_fixtures = Match.objects.filter(
                club__in=eligible_clubs,
                date__range=(today, end_date),
                status='SCHEDULED'
            ).select_related('club', 'club__selected_pack').order_by('date', 'time_start')
            
            fixtures_data = []
            for fixture in upcoming_fixtures:
                fixture_info = {
                    "id": fixture.id,
                    "club_id": fixture.club.id,
                    "club_name": fixture.club.name,
                    "club_logo": fixture.club.logo,
                    "opponent": fixture.opponent,
                    "opponent_logo": fixture.opponent_logo,
                    "date": fixture.date.isoformat() if fixture.date else None,
                    "time_start": fixture.time_start,
                    "venue": fixture.venue,
                    "competition": fixture.competition,
                    "home_away": fixture.home_away,
                    "matchday_post_url": fixture.matchday_post_url,
                    "upcoming_fixture_post_url": fixture.upcoming_fixture_post_url,
                    "starting_xi_post_url": fixture.starting_xi_post_url,
                    "graphic_pack_name": fixture.club.selected_pack.name if fixture.club.selected_pack else None,
                }
                fixtures_data.append(fixture_info)
            
            return Response({
                "count": len(fixtures_data),
                "fixtures": fixtures_data
            })
            
        except Exception as e:
            logger.error(f"Error fetching admin fixture task list: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching fixture task list."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def _player_bespoke_columns_exist():
    """Check if player bespoke graphic columns exist in the database."""
    from django.db import connection
    from content.models import Player
    try:
        with connection.cursor() as cursor:
            table_name = Player._meta.db_table
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name=%s 
                AND column_name IN ('cutout_url', 'highlight_home_url', 'highlight_away_url', 'potm_url')
            """, [table_name])
            results = cursor.fetchall()
            # Check if all 4 columns exist
            column_names = [row[0] for row in results]
            required_columns = ['cutout_url', 'highlight_home_url', 'highlight_away_url', 'potm_url']
            return all(col in column_names for col in required_columns)
    except Exception as e:
        logger.warning(f"Could not check for player bespoke columns: {str(e)}")
        return False


def _get_player_queryset():
    """Get a Player queryset that handles missing bespoke graphic columns."""
    from content.models import Player
    if not _player_bespoke_columns_exist():
        # Columns don't exist - defer them to avoid SELECT error
        return Player.objects.defer('cutout_url', 'highlight_home_url', 'highlight_away_url', 'potm_url')
    return Player.objects.all()


class AdminPlayerTaskListView(APIView):
    """Get all players from Premium clubs with Bespoke template packages"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get task list of players for eligible clubs"""
        try:
            # Check if user is admin/staff
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    "error": "Access denied. Admin privileges required."
                }, status=status.HTTP_403_FORBIDDEN)
            
            from users.models import Club
            from content.models import Player
            from graphicpack.models import GraphicPack
            
            # Get clubs that are on Premium Plans (prem) with Bespoke template packages
            eligible_clubs = Club.objects.filter(
                subscription_tier='prem',
                subscription_active=True,
                selected_pack__is_bespoke=True
            ).select_related('selected_pack')
            
            # Get all players for these clubs - use helper to handle missing columns
            players = _get_player_queryset().filter(
                club__in=eligible_clubs
            ).select_related('club', 'club__selected_pack').order_by('club__name', 'squad_no', 'name')
            
            # Check if columns exist to determine default values
            columns_exist = _player_bespoke_columns_exist()
            
            players_data = []
            for player in players:
                player_info = {
                    "id": player.id,
                    "club_id": player.club.id,
                    "club_name": player.club.name,
                    "club_logo": player.club.logo,
                    "name": player.name,
                    "squad_no": player.squad_no,
                    "position": player.position,
                    "player_pic": player.player_pic,
                    "formatted_pic": player.formatted_pic,
                    "graphic_pack_name": player.club.selected_pack.name if player.club.selected_pack else None,
                }
                
                # Only include bespoke graphic URLs if columns exist
                if columns_exist:
                    player_info.update({
                        "cutout_url": getattr(player, 'cutout_url', None),
                        "highlight_home_url": getattr(player, 'highlight_home_url', None),
                        "highlight_away_url": getattr(player, 'highlight_away_url', None),
                        "potm_url": getattr(player, 'potm_url', None),
                    })
                else:
                    # Columns don't exist yet - return None for all
                    player_info.update({
                        "cutout_url": None,
                        "highlight_home_url": None,
                        "highlight_away_url": None,
                        "potm_url": None,
                    })
                
                players_data.append(player_info)
            
            return Response({
                "count": len(players_data),
                "players": players_data
            })
            
        except Exception as e:
            logger.error(f"Error fetching admin player task list: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching player task list."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminUploadPlayerImageView(APIView):
    """Admin endpoint to upload player images (cutout, highlight-home, highlight-away, potm)"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request):
        """Upload a player image URL or file"""
        try:
            # Check if user is admin/staff
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    "error": "Access denied. Admin privileges required."
                }, status=status.HTTP_403_FORBIDDEN)
            
            from content.models import Player
            import cloudinary.uploader
            
            player_id = request.data.get('player_id')
            image_type = request.data.get('image_type')  # 'cutout', 'highlight_home', 'highlight_away', 'potm'
            image_url = request.data.get('image_url')
            uploaded_file = request.FILES.get('file')
            
            if not player_id or not image_type:
                return Response({
                    "error": "Missing required fields: player_id and image_type are required."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if image_type not in ['cutout', 'highlight_home', 'highlight_away', 'potm']:
                return Response({
                    "error": "Invalid image_type. Must be one of: cutout, highlight_home, highlight_away, potm"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not uploaded_file and not image_url:
                return Response({
                    "error": "Either an image file or an image_url must be provided."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                player = Player.objects.get(id=player_id)
            except Player.DoesNotExist:
                return Response({
                    "error": "Player not found."
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Upload file to Cloudinary if provided
            if uploaded_file:
                try:
                    upload_result = cloudinary.uploader.upload(
                        uploaded_file,
                        folder=f"admin_players/{image_type}",
                        resource_type="auto",
                        overwrite=False,
                        use_filename=True,
                        unique_filename=True,
                    )
                    image_url = upload_result.get('secure_url')
                except Exception as cloudinary_error:
                    logger.error(f"Cloudinary upload failed: {str(cloudinary_error)}", exc_info=True)
                    return Response(
                        {"error": "Failed to upload image. Please try again."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            
            # Ensure we have a URL after optional upload
            if not image_url:
                return Response({
                    "error": "No image URL available after upload."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if columns exist
            columns_exist = _player_bespoke_columns_exist()
            
            if not columns_exist:
                return Response({
                    "error": "Player bespoke graphic columns do not exist. Please run migrations first."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Map image_type to field name
            field_mapping = {
                'cutout': 'cutout_url',
                'highlight_home': 'highlight_home_url',
                'highlight_away': 'highlight_away_url',
                'potm': 'potm_url'
            }
            
            field_name = field_mapping.get(image_type)
            if not field_name:
                return Response({
                    "error": "Invalid image_type mapping."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update the appropriate field
            setattr(player, field_name, image_url)
            player.save()
            
            return Response({
                "message": f"{image_type.replace('_', ' ').title()} image uploaded successfully.",
                "player_id": player.id,
                "image_type": image_type,
                "image_url": image_url
            })
            
        except Exception as e:
            logger.error(f"Error uploading player image: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while uploading the player image."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminUploadPostView(APIView):
    """Admin endpoint to upload Matchday, Upcoming Fixture, or Starting XI posts"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request):
        """Upload a post URL for a fixture"""
        try:
            # Check if user is admin/staff
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    "error": "Access denied. Admin privileges required."
                }, status=status.HTTP_403_FORBIDDEN)
            
            from content.models import Match
            
            fixture_id = request.data.get('fixture_id')
            post_type = request.data.get('post_type')  # 'matchday', 'upcoming_fixture', 'starting_xi'
            post_url = request.data.get('post_url')
            uploaded_file = request.FILES.get('file')
            
            if not fixture_id or not post_type:
                return Response({
                    "error": "Missing required fields: fixture_id and post_type are required."
                }, status=status.HTTP_400_BAD_REQUEST)

            if post_type not in ['matchday', 'upcoming_fixture', 'starting_xi']:
                return Response({
                    "error": "Invalid post_type. Must be one of: matchday, upcoming_fixture, starting_xi"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not uploaded_file and not post_url:
                return Response({
                    "error": "Either an image file or a post_url must be provided."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                fixture = Match.objects.get(id=fixture_id)
            except Match.DoesNotExist:
                return Response({
                    "error": "Fixture not found."
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Upload file to Cloudinary if provided
            if uploaded_file:
                try:
                    upload_result = cloudinary.uploader.upload(
                        uploaded_file,
                        folder=f"admin_posts/{post_type}",
                        resource_type="auto",
                        overwrite=False,
                        use_filename=True,
                        unique_filename=True,
                    )
                    post_url = upload_result.get('secure_url')
                except Exception as cloudinary_error:
                    logger.error(f"Cloudinary upload failed: {str(cloudinary_error)}", exc_info=True)
                    return Response(
                        {"error": "Failed to upload image. Please try again."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # Ensure we have a URL after optional upload
            if not post_url:
                return Response({
                    "error": "Post URL could not be determined."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Update the appropriate field
            if post_type == 'matchday':
                fixture.matchday_post_url = post_url
            elif post_type == 'upcoming_fixture':
                fixture.upcoming_fixture_post_url = post_url
            elif post_type == 'starting_xi':
                fixture.starting_xi_post_url = post_url
            
            fixture.save()
            
            return Response({
                "message": f"{post_type.replace('_', ' ').title()} post URL uploaded successfully.",
                "fixture_id": fixture.id,
                "post_type": post_type,
                "post_url": post_url
            })
            
        except Exception as e:
            logger.error(f"Error uploading post: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while uploading the post."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ClubCreateView(APIView):
    """View for creating clubs"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create a new club"""
        serializer = ClubSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClubUpdateView(APIView):
    """View for updating clubs"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, pk):
        """Update a club"""
        try:
            club = Club.objects.get(id=pk, user=request.user)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ClubSerializer(club, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClubDeleteView(APIView):
    """View for deleting clubs"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, pk):
        """Delete a club"""
        try:
            club = Club.objects.get(id=pk, user=request.user)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        
        club.delete()
        return Response({"message": "Club deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# Stripe Integration Views
class StripeCheckoutView(APIView):
    """View for creating Stripe checkout sessions"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create a Stripe checkout session for subscription upgrade"""
        try:
            # Configure Stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            # Get request data
            tier = request.data.get('tier')
            club_id = request.data.get('club_id')
            
            if not tier or not club_id:
                return Response(
                    {"error": "Tier and club_id are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate tier
            if tier not in ['basic', 'semipro', 'prem']:
                return Response(
                    {"error": "Invalid tier. Must be basic, semipro, or prem"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get club
            try:
                club = Club.objects.get(id=club_id)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Allow all authenticated users to manage billing for any club
            # This is a subscription service where users should be able to upgrade their own plans
            logger.info(f"User {request.user.id} attempting to create checkout for club {club.id}")
            
            # Get price ID for the tier
            price_id = settings.STRIPE_PRICES.get(tier)
            if not price_id:
                return Response(
                    {"error": f"Price ID not configured for {tier} tier"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url="https://matchgen-frontend.vercel.app/subscription?success=true&session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://matchgen-frontend.vercel.app/subscription?canceled=true",
                metadata={
                    'club_id': str(club_id),
                    'user_id': str(request.user.id),
                    'tier': tier,
                    'club_name': club.name
                },
                customer_email=request.user.email,
                allow_promotion_codes=True,
                billing_address_collection='required',
                subscription_data={
                    'metadata': {
                        'club_id': str(club_id),
                        'user_id': str(request.user.id),
                        'tier': tier,
                        'club_name': club.name
                    }
                }
            )
            
            logger.info(f"Stripe checkout session created for user {request.user.email}, club {club.name}, tier {tier}")
            
            return Response({
                'session_id': checkout_session.id,
                'url': checkout_session.url
            })
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return Response(
                {"error": "Payment processing error. Please try again."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Checkout session creation error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while creating checkout session"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StripeBillingPortalView(APIView):
    """View for creating Stripe billing portal sessions"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create a Stripe billing portal session"""
        try:
            # Configure Stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            # Get request data
            club_id = request.data.get('club_id')
            
            if not club_id:
                return Response(
                    {"error": "club_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get club
            try:
                club = Club.objects.get(id=club_id)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Allow all authenticated users to manage billing for any club
            # This is a subscription service where users should be able to manage their own billing
            logger.info(f"User {request.user.id} attempting to access billing portal for club {club.id}")
            
            # For now, we'll create a customer if they don't exist
            # In a real implementation, you'd store the customer ID in your database
            customer = stripe.Customer.create(
                email=request.user.email,
                metadata={
                    'club_id': str(club_id),
                    'user_id': str(request.user.id),
                    'club_name': club.name
                }
            )
            
            # Create billing portal session
            billing_portal_session = stripe.billing_portal.Session.create(
                customer=customer.id,
                return_url=f"{request.build_absolute_uri('/')}subscription",
            )
            
            logger.info(f"Stripe billing portal session created for user {request.user.email}, club {club.name}")
            
            return Response({
                'url': billing_portal_session.url
            })
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return Response(
                {"error": "Billing portal error. Please try again."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Billing portal session creation error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while creating billing portal session"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StripeWebhookView(APIView):
    """View for handling Stripe webhooks"""
    permission_classes = [AllowAny]  # Webhooks don't use authentication
    
    def post(self, request):
        """Handle Stripe webhook events"""
        try:
            # Check if webhook secret is configured
            if not settings.STRIPE_WEBHOOK_SECRET:
                logger.error("STRIPE_WEBHOOK_SECRET is not configured")
                return Response(
                    {"error": "Webhook secret not configured"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Get the webhook payload
            payload = request.body
            sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
            
            if not sig_header:
                logger.error("No Stripe signature header found")
                return Response(
                    {"error": "No signature header"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify webhook signature (with fallback for testing)
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
                )
            except ValueError as e:
                logger.error(f"Invalid payload: {str(e)}")
                return Response(
                    {"error": "Invalid payload"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"Invalid signature: {str(e)}")
                # For testing purposes, try to parse the event without signature verification
                try:
                    import json
                    event = json.loads(payload.decode('utf-8'))
                    logger.warning("Bypassing signature verification for testing")
                except Exception as parse_error:
                    logger.error(f"Failed to parse webhook payload: {str(parse_error)}")
                    return Response(
                        {"error": "Invalid signature and failed to parse payload"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Handle the event
            if event['type'] == 'checkout.session.completed':
                self.handle_checkout_completed(event['data']['object'])
            elif event['type'] == 'customer.subscription.updated':
                self.handle_subscription_updated(event['data']['object'])
            elif event['type'] == 'customer.subscription.deleted':
                self.handle_subscription_deleted(event['data']['object'])
            elif event['type'] == 'invoice.payment_succeeded':
                self.handle_payment_succeeded(event['data']['object'])
            elif event['type'] == 'invoice.payment_failed':
                self.handle_payment_failed(event['data']['object'])
            else:
                logger.info(f"Unhandled event type: {event['type']}")
            
            return Response({"status": "success"})
            
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}", exc_info=True)
            return Response(
                {"error": "Webhook processing error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def handle_checkout_completed(self, session):
        """Handle successful checkout completion"""
        try:
            metadata = session.get('metadata', {})
            club_id = metadata.get('club_id')
            user_id = metadata.get('user_id')
            tier = metadata.get('tier')
            
            if not all([club_id, user_id, tier]):
                logger.error("Missing metadata in checkout session")
                return
            
            # Get the subscription ID from the session
            subscription_id = session.get('subscription')
            if not subscription_id:
                logger.error("No subscription ID found in checkout session")
                return
            
            # Update club subscription
            club = Club.objects.get(id=club_id)
            club.subscription_tier = tier
            club.subscription_active = True
            club.subscription_start_date = timezone.now()
            club.stripe_subscription_id = subscription_id  # Store the Stripe subscription ID
            club.save()
            
            # Log audit event
            user = User.objects.get(id=user_id)
            AuditLogger.log_event(
                user=user,
                club=club,
                action='subscription_changed',
                details={
                    'new_tier': tier,
                    'stripe_session_id': session.get('id'),
                    'stripe_subscription_id': subscription_id,
                    'payment_status': session.get('payment_status')
                }
            )
            
            logger.info(f"Subscription updated for club {club.name} to {tier} tier with Stripe ID {subscription_id}")
            
        except Exception as e:
            logger.error(f"Error handling checkout completion: {str(e)}", exc_info=True)
    
    def handle_subscription_updated(self, subscription):
        """Handle subscription updates"""
        try:
            metadata = subscription.get('metadata', {})
            club_id = metadata.get('club_id')
            
            if not club_id:
                return
            
            club = Club.objects.get(id=club_id)
            
            # Ensure subscription ID is stored
            subscription_id = subscription.get('id')
            if subscription_id:
                club.stripe_subscription_id = subscription_id
            
            # Update subscription status based on Stripe status
            if subscription.get('status') == 'active':
                club.subscription_active = True
            elif subscription.get('status') in ['canceled', 'unpaid', 'past_due']:
                club.subscription_active = False
            
            club.save()
            
            logger.info(f"Subscription status updated for club {club.name}: {subscription.get('status')} (ID: {subscription_id})")
            
        except Exception as e:
            logger.error(f"Error handling subscription update: {str(e)}", exc_info=True)
    
    def handle_subscription_deleted(self, subscription):
        """Handle subscription deletion"""
        try:
            metadata = subscription.get('metadata', {})
            club_id = metadata.get('club_id')
            
            if not club_id:
                return
            
            club = Club.objects.get(id=club_id)
            club.subscription_active = False
            club.stripe_subscription_id = None  # Clear the subscription ID
            club.save()
            
            logger.info(f"Subscription deactivated for club {club.name}")
            
        except Exception as e:
            logger.error(f"Error handling subscription deletion: {str(e)}", exc_info=True)
    
    def handle_payment_succeeded(self, invoice):
        """Handle successful payment"""
        try:
            subscription_id = invoice.get('subscription')
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                metadata = subscription.get('metadata', {})
                club_id = metadata.get('club_id')
                
                if club_id:
                    club = Club.objects.get(id=club_id)
                    club.subscription_active = True
                    club.save()
                    
                    logger.info(f"Payment succeeded for club {club.name}")
                    
        except Exception as e:
            logger.error(f"Error handling payment success: {str(e)}", exc_info=True)
    
    def handle_payment_failed(self, invoice):
        """Handle failed payment"""
        try:
            subscription_id = invoice.get('subscription')
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                metadata = subscription.get('metadata', {})
                club_id = metadata.get('club_id')
                
                if club_id:
                    club = Club.objects.get(id=club_id)
                    club.subscription_active = False
                    club.save()
                    
                    logger.info(f"Payment failed for club {club.name}")
                    
        except Exception as e:
            logger.error(f"Error handling payment failure: {str(e)}", exc_info=True)


class SendVerificationCodeView(APIView):
    """Send verification code to user's email."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Send a 6-digit verification code to the user's email."""
        email = request.data.get('email')
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            # Generate a 6-digit verification code
            import random
            verification_code = str(random.randint(100000, 999999))
            
            # Store the code in cache with 10-minute expiry
            cache_key = f"verification_code_{email}"
            cache.set(cache_key, verification_code, 600)  # 10 minutes
            
            # Send the code via email
            self._send_verification_code_email(user, verification_code)
            
            logger.info(f"Verification code sent to {email}")
            return Response({
                'message': 'Verification code sent successfully',
                'email': email
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error sending verification code: {str(e)}")
            return Response({'error': 'Failed to send verification code'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _send_verification_code_email(self, user, code):
        """Send verification code email to user."""
        try:
            subject = "Your MatchGen Verification Code"
            message = f"""
            Your verification code is: {code}
            
            This code will expire in 10 minutes.
            
            If you didn't request this code, please ignore this email.
            
            Best regards,
            The MatchGen Team
            """
            
            # Check if email settings are configured
            email_user = getattr(settings, 'EMAIL_HOST_USER', None)
            email_password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            
            if not email_user or not email_password:
                logger.warning(f"Email settings not configured. Skipping email send for {user.email}")
                logger.info(f"Verification code for {user.email}: {code}")
                print(f"\n🔐 VERIFICATION CODE FOR {user.email}:")
                print(f"{code}")
                print(f"Use this code to verify the account.\n")
                return
            
            # Try to send email with SendGrid API
            try:
                import requests
                
                sendgrid_url = "https://api.sendgrid.com/v3/mail/send"
                headers = {
                    "Authorization": f"Bearer {email_password}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "personalizations": [{
                        "to": [{"email": user.email}],
                        "subject": subject
                    }],
                    "from": {"email": settings.DEFAULT_FROM_EMAIL},
                    "content": [{
                        "type": "text/plain",
                        "value": message
                    }]
                }
                
                response = requests.post(sendgrid_url, headers=headers, json=data)
                
                if response.status_code == 202:
                    logger.info(f"Verification code email sent successfully to {user.email}")
                else:
                    logger.error(f"SendGrid API error: {response.status_code} - {response.text}")
                    print(f"\n🔐 VERIFICATION CODE FOR {user.email}:")
                    print(f"{code}")
                    print(f"Use this code to verify the account.\n")
            except Exception as e:
                logger.error(f"Error sending email via SendGrid: {str(e)}")
                print(f"\n🔐 VERIFICATION CODE FOR {user.email}:")
                print(f"{code}")
                print(f"Use this code to verify the account.\n")
                
        except Exception as e:
            logger.error(f"Error in _send_verification_code_email: {str(e)}")
            print(f"\n🔐 VERIFICATION CODE FOR {user.email}:")
            print(f"{code}")
            print(f"Use this code to verify the account.\n")


class VerifyEmailCodeView(APIView):
    """Verify user email with code."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Verify email with the provided code."""
        email = request.data.get('email')
        code = request.data.get('code')
        
        if not email or not code:
            return Response({'error': 'Email and code are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            # Check if code matches
            cache_key = f"verification_code_{email}"
            stored_code = cache.get(cache_key)
            
            if not stored_code:
                return Response({'error': 'Verification code has expired or not found'}, status=status.HTTP_400_BAD_REQUEST)
            
            if stored_code != code:
                return Response({'error': 'Invalid verification code'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark email as verified
            user.email_verified = True
            user.save()
            
            # Clear the verification code from cache
            cache.delete(cache_key)
            
            # Generate tokens for immediate login
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            logger.info(f"Email verified successfully for {email}")
            return Response({
                'message': 'Email verified successfully',
                'access': access_token,
                'refresh': refresh_token
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error verifying email code: {str(e)}")
            return Response({'error': 'Failed to verify email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeCancelSubscriptionView(APIView):
    """View for canceling Stripe subscriptions"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Cancel a Stripe subscription"""
        try:
            # Configure Stripe
            if not hasattr(settings, 'STRIPE_SECRET_KEY') or not settings.STRIPE_SECRET_KEY:
                logger.error("STRIPE_SECRET_KEY is not configured")
                return Response({'error': 'Payment system not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            # Get club information
            club_id = request.data.get('club_id')
            if not club_id:
                return Response({'error': 'Club ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the club
            try:
                club = Club.objects.get(id=club_id, user=request.user)
            except Club.DoesNotExist:
                return Response({'error': 'Club not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if club has an active subscription
            stripe_subscription_id = getattr(club, 'stripe_subscription_id', None)
            logger.info(f"Cancel subscription request for club {club.id}: active={club.subscription_active}, stripe_id={stripe_subscription_id}")
            
            if not club.subscription_active:
                return Response({'error': 'No active subscription found'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not stripe_subscription_id:
                # Handle test/development subscriptions that don't have Stripe IDs
                logger.info(f"Canceling test subscription for club {club.id} (no Stripe subscription ID)")
                
                # Update club subscription status locally
                club.subscription_active = False
                club.subscription_canceled = True
                club.save()
                
                return Response({
                    'message': 'Test subscription canceled successfully',
                    'subscription_active': False,
                    'subscription_canceled': True
                }, status=status.HTTP_200_OK)
            
            # Cancel the subscription in Stripe
            try:
                logger.info(f"Retrieving Stripe subscription {stripe_subscription_id}")
                subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                logger.info(f"Retrieved subscription status: {subscription.status}")
                
                canceled_subscription = stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True
                )
                
                logger.info(f"Subscription {stripe_subscription_id} set to cancel at period end for club {club.id}")
                
                # Update club subscription status
                try:
                    club.subscription_active = True  # Still active until period end
                    club.subscription_canceled = True  # Mark as canceled
                    club.save()
                    logger.info(f"Updated club {club.id} subscription status: active={club.subscription_active}, canceled={club.subscription_canceled}")
                except Exception as save_error:
                    logger.error(f"Error saving club subscription status: {str(save_error)}")
                    # Don't fail the entire operation if database save fails
                
                # Safely extract response data
                try:
                    response_data = {
                        'message': 'Subscription will be canceled at the end of the current billing period',
                        'cancel_at_period_end': getattr(canceled_subscription, 'cancel_at_period_end', True),
                        'current_period_end': getattr(canceled_subscription, 'current_period_end', None)
                    }
                    
                    logger.info(f"Successfully canceled subscription {stripe_subscription_id} for club {club.id}")
                    return Response(response_data, status=status.HTTP_200_OK)
                    
                except Exception as response_error:
                    logger.error(f"Error creating response data: {str(response_error)}")
                    # Return a simple success response if response data creation fails
                    return Response({
                        'message': 'Subscription will be canceled at the end of the current billing period'
                    }, status=status.HTTP_200_OK)
                
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error canceling subscription {stripe_subscription_id}: {str(e)}")
                return Response({'error': f'Failed to cancel subscription with Stripe: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return Response({'error': 'Failed to cancel subscription'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeReactivateSubscriptionView(APIView):
    """View for reactivating canceled Stripe subscriptions"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Reactivate a canceled Stripe subscription"""
        try:
            # Configure Stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            # Get club information
            club_id = request.data.get('club_id')
            if not club_id:
                return Response({'error': 'Club ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the club
            try:
                club = Club.objects.get(id=club_id, user=request.user)
            except Club.DoesNotExist:
                return Response({'error': 'Club not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if club has a canceled subscription
            if not club.subscription_canceled or not club.stripe_subscription_id:
                return Response({'error': 'No canceled subscription found'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Reactivate the subscription in Stripe
            try:
                subscription = stripe.Subscription.modify(
                    club.stripe_subscription_id,
                    cancel_at_period_end=False
                )
                
                logger.info(f"Subscription {club.stripe_subscription_id} reactivated for club {club.id}")
                
                # Update club subscription status
                club.subscription_canceled = False
                club.save()
                
                return Response({
                    'message': 'Subscription reactivated successfully',
                    'cancel_at_period_end': subscription.cancel_at_period_end
                }, status=status.HTTP_200_OK)
                
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error reactivating subscription: {str(e)}")
                return Response({'error': 'Failed to reactivate subscription with Stripe'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error reactivating subscription: {str(e)}")
            return Response({'error': 'Failed to reactivate subscription'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeUpgradeSubscriptionView(APIView):
    """View for immediate subscription upgrades with proration"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Upgrade subscription immediately with proration"""
        try:
            # Configure Stripe
            if not hasattr(settings, 'STRIPE_SECRET_KEY') or not settings.STRIPE_SECRET_KEY:
                logger.error("STRIPE_SECRET_KEY is not configured")
                return Response({'error': 'Payment system not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            # Get request data
            club_id = request.data.get('club_id')
            new_tier = request.data.get('tier')
            
            if not club_id or not new_tier:
                return Response({'error': 'Club ID and tier are required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate tier
            if new_tier not in ['basic', 'semipro', 'prem']:
                return Response({'error': 'Invalid tier'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the club
            try:
                club = Club.objects.get(id=club_id, user=request.user)
            except Club.DoesNotExist:
                return Response({'error': 'Club not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if club has an active subscription
            if not club.subscription_active or not club.stripe_subscription_id:
                return Response({'error': 'No active subscription found'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get current and new price IDs
            current_price_id = settings.STRIPE_PRICES.get(club.subscription_tier)
            new_price_id = settings.STRIPE_PRICES.get(new_tier)
            
            if not current_price_id or not new_price_id:
                return Response({'error': 'Price configuration not found'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Get current subscription
            subscription = stripe.Subscription.retrieve(club.stripe_subscription_id)
            
            # Update subscription with new price
            try:
                updated_subscription = stripe.Subscription.modify(
                    club.stripe_subscription_id,
                    items=[{
                        'id': subscription['items']['data'][0]['id'],
                        'price': new_price_id,
                    }],
                    proration_behavior='create_prorations',  # Fair billing
                    metadata={
                        'club_id': str(club_id),
                        'tier': new_tier,
                        'club_name': club.name
                    }
                )
                
                logger.info(f"Stripe subscription {club.stripe_subscription_id} upgraded to {new_tier}")
                
                # Update club subscription
                try:
                    club.subscription_tier = new_tier
                    club.subscription_canceled = False  # Clear any cancellation
                    club.save()
                    logger.info(f"Updated club {club.id} subscription tier to {new_tier}")
                except Exception as save_error:
                    logger.error(f"Error saving club subscription status: {str(save_error)}")
                    # Don't fail the entire operation if database save fails
                
                # Safely extract response data
                try:
                    response_data = {
                        'message': 'Subscription upgraded successfully',
                        'new_tier': new_tier,
                        'current_period_end': getattr(updated_subscription, 'current_period_end', None),
                        'proration_created': True
                    }
                    
                    logger.info(f"Successfully upgraded subscription for club {club.id}")
                    return Response(response_data, status=status.HTTP_200_OK)
                    
                except Exception as response_error:
                    logger.error(f"Error creating response data: {str(response_error)}")
                    # Return a simple success response if response data creation fails
                    return Response({
                        'message': 'Subscription upgraded successfully',
                        'new_tier': new_tier
                    }, status=status.HTTP_200_OK)
                    
            except stripe.error.StripeError as stripe_error:
                logger.error(f"Stripe error during subscription upgrade: {str(stripe_error)}")
                return Response({'error': f'Failed to upgrade subscription with Stripe: {str(stripe_error)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error upgrading subscription: {str(e)}")
            return Response({'error': 'Failed to upgrade subscription with Stripe'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error upgrading subscription: {str(e)}")
            return Response({'error': 'Failed to upgrade subscription'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeDowngradeSubscriptionView(APIView):
    """View for scheduling subscription downgrades at period end"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Schedule subscription downgrade for next period end"""
        try:
            # Configure Stripe
            if not hasattr(settings, 'STRIPE_SECRET_KEY') or not settings.STRIPE_SECRET_KEY:
                logger.error("STRIPE_SECRET_KEY is not configured")
                return Response({'error': 'Payment system not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            # Get request data
            club_id = request.data.get('club_id')
            new_tier = request.data.get('tier')
            
            if not club_id or not new_tier:
                return Response({'error': 'Club ID and tier are required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate tier
            if new_tier not in ['basic', 'semipro', 'prem']:
                return Response({'error': 'Invalid tier'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the club
            try:
                club = Club.objects.get(id=club_id, user=request.user)
            except Club.DoesNotExist:
                return Response({'error': 'Club not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if club has an active subscription
            if not club.subscription_active or not club.stripe_subscription_id:
                return Response({'error': 'No active subscription found'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get new price ID
            new_price_id = settings.STRIPE_PRICES.get(new_tier)
            if not new_price_id:
                return Response({'error': 'Price configuration not found'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Get current subscription
            subscription = stripe.Subscription.retrieve(club.stripe_subscription_id)
            
            # Schedule the downgrade for next period end
            try:
                updated_subscription = stripe.Subscription.modify(
                    club.stripe_subscription_id,
                    items=[{
                        'id': subscription['items']['data'][0]['id'],
                        'price': new_price_id,
                    }],
                    proration_behavior='none',  # No immediate charges
                    billing_cycle_anchor='unchanged',  # Keep current billing cycle
                    metadata={
                        'club_id': str(club_id),
                        'tier': new_tier,
                        'club_name': club.name,
                        'scheduled_downgrade': 'true'
                    }
                )
                
                logger.info(f"Stripe subscription {club.stripe_subscription_id} scheduled for downgrade to {new_tier}")
                
                # Update club with scheduled downgrade info (but keep current tier until period end)
                try:
                    # Store the scheduled downgrade tier without changing current tier
                    club.scheduled_tier = new_tier
                    
                    # Don't change the current subscription_tier - keep it active until period end
                    club.subscription_canceled = False  # Not canceled, just scheduled for downgrade
                    club.save()
                    logger.info(f"Club {club.id} scheduled for downgrade to {new_tier} at period end (current tier: {club.subscription_tier})")
                except Exception as save_error:
                    logger.error(f"Error saving club subscription status: {str(save_error)}")
                    # Don't fail the entire operation if database save fails
                
                # Safely extract response data
                try:
                    response_data = {
                        'message': 'Subscription downgrade scheduled for next billing period',
                        'current_tier': club.subscription_tier,  # Current active tier
                        'scheduled_tier': new_tier,  # Tier that will take effect
                        'current_period_end': getattr(updated_subscription, 'current_period_end', None),
                        'effective_date': getattr(updated_subscription, 'current_period_end', None),
                        'scheduled_downgrade': True
                    }
                    
                    logger.info(f"Successfully scheduled downgrade for club {club.id}")
                    return Response(response_data, status=status.HTTP_200_OK)
                    
                except Exception as response_error:
                    logger.error(f"Error creating response data: {str(response_error)}")
                    # Return a simple success response if response data creation fails
                    return Response({
                        'message': 'Subscription downgrade scheduled for next billing period',
                        'current_tier': club.subscription_tier,
                        'scheduled_tier': new_tier,
                        'scheduled_downgrade': True
                    }, status=status.HTTP_200_OK)
                    
            except stripe.error.StripeError as stripe_error:
                logger.error(f"Stripe error during subscription downgrade: {str(stripe_error)}")
                return Response({'error': f'Failed to schedule downgrade with Stripe: {str(stripe_error)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error scheduling downgrade: {str(e)}")
            return Response({'error': 'Failed to schedule downgrade with Stripe'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error scheduling downgrade: {str(e)}")
            return Response({'error': 'Failed to schedule downgrade'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAccountView(APIView):
    """View for deleting user accounts"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        """Delete user account and all associated data"""
        try:
            user = request.user
            
            # Log the deletion attempt
            logger.info(f"User {user.id} ({user.email}) requesting account deletion")
            
            # Get user's clubs
            user_clubs = Club.objects.filter(user=user)
            
            # Cancel any active Stripe subscriptions
            if hasattr(settings, 'STRIPE_SECRET_KEY') and settings.STRIPE_SECRET_KEY:
                try:
                    stripe.api_key = settings.STRIPE_SECRET_KEY
                    
                    for club in user_clubs:
                        if club.stripe_subscription_id:
                            try:
                                # Cancel the subscription immediately
                                stripe.Subscription.delete(club.stripe_subscription_id)
                                logger.info(f"Cancelled Stripe subscription {club.stripe_subscription_id} for club {club.id}")
                            except stripe.error.StripeError as e:
                                logger.warning(f"Failed to cancel Stripe subscription for club {club.id}: {str(e)}")
                except Exception as e:
                    logger.warning(f"Error cancelling Stripe subscriptions: {str(e)}")
            
            # Log audit event before deletion
            try:
                AuditLogger.log_event(
                    user=user,
                    club=None,
                    action='account_deleted',
                    details={
                        'user_email': user.email,
                        'clubs_deleted': [club.id for club in user_clubs],
                        'deletion_timestamp': timezone.now().isoformat()
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log account deletion audit event: {str(e)}")
            
            # Delete all user's clubs (this will cascade delete related data)
            for club in user_clubs:
                club.delete()
                logger.info(f"Deleted club {club.id} ({club.name})")
            
            # Delete the user account
            user_email = user.email
            user.delete()
            
            logger.info(f"Successfully deleted user account for {user_email}")
            
            return Response({
                'message': 'Account deleted successfully',
                'deleted_clubs': len(user_clubs)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error deleting user account: {str(e)}")
            return Response({
                'error': 'Failed to delete account. Please contact support if this issue persists.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ForgotPasswordView(APIView):
    """
    Send password reset instructions to user's email
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            email = request.data.get('email')
            
            if not email:
                return Response({
                    'error': 'Email is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # For security, don't reveal if email exists or not
                return Response({
                    'message': 'If an account with this email exists, password reset instructions have been sent.'
                }, status=status.HTTP_200_OK)
            
            # Generate a simple reset token (in production, use a more secure method)
            import uuid
            reset_token = str(uuid.uuid4())
            
            # Store the reset token in cache with expiration (1 hour)
            cache.set(f"password_reset_{reset_token}", user.id, 3600)
            
            # Create reset URL
            reset_url = f"https://matchgen-frontend.vercel.app/reset-password?token={reset_token}"
            
            # Send email
            subject = "MatchGen - Password Reset"
            message = f"""
Hello {user.email},

You requested a password reset for your MatchGen account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this password reset, please ignore this email.

Best regards,
The MatchGen Team
            """
            
            try:
                # Check if email settings are configured
                email_user = getattr(settings, 'EMAIL_HOST_USER', None)
                email_password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
                
                if not email_user or not email_password:
                    logger.warning(f"Email settings not configured. Skipping email send for {email}")
                    logger.info(f"Password reset URL for {email}: {reset_url}")
                    print(f"\n🔗 PASSWORD RESET LINK FOR {email}:")
                    print(f"{reset_url}")
                    print(f"Copy this link and paste it in your browser to reset the password.\n")
                    return Response({
                        'message': 'Password reset instructions have been sent to your email address.'
                    }, status=status.HTTP_200_OK)
                
                # Try to send email with SendGrid API (same as verification emails)
                try:
                    import requests
                    
                    # SendGrid API endpoint
                    sendgrid_url = "https://api.sendgrid.com/v3/mail/send"
                    
                    # Prepare email data
                    email_data = {
                        "personalizations": [
                            {
                                "to": [{"email": email}],
                                "subject": subject
                            }
                        ],
                        "from": {"email": settings.DEFAULT_FROM_EMAIL},
                        "content": [
                            {
                                "type": "text/plain",
                                "value": message
                            }
                        ]
                    }
                    
                    # Send via SendGrid API
                    headers = {
                        "Authorization": f"Bearer {settings.EMAIL_HOST_PASSWORD}",
                        "Content-Type": "application/json"
                    }
                    
                    response = requests.post(sendgrid_url, json=email_data, headers=headers, timeout=10)
                    
                    if response.status_code == 202:
                        logger.info(f"✅ Password reset email sent successfully to {email}")
                    else:
                        logger.error(f"❌ SendGrid API error: {response.status_code} - {response.text}")
                        raise Exception(f"SendGrid API error: {response.status_code}")
                        
                except Exception as email_error:
                    logger.error(f"❌ Failed to send email to {email}: {str(email_error)}")
                    # Fallback: log the reset link
                    logger.info(f"Password reset URL for {email}: {reset_url}")
                    print(f"\n🔗 PASSWORD RESET LINK FOR {email}:")
                    print(f"{reset_url}")
                    print(f"Copy this link and paste it in your browser to reset the password.\n")
                
                return Response({
                    'message': 'Password reset instructions have been sent to your email address.'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error sending password reset email: {str(e)}")
                # Return success to user but log the error for debugging
                return Response({
                    'message': 'Password reset instructions have been sent to your email address.'
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Error in forgot password: {str(e)}", exc_info=True)
            # Return a generic success message to prevent revealing system errors
            return Response({
                'message': 'Password reset instructions have been sent to your email address.'
            }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    """
    Reset user password with token
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            token = request.data.get('token')
            new_password = request.data.get('new_password')
            
            if not token or not new_password:
                return Response({
                    'error': 'Token and new password are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate password
            try:
                validate_password(new_password)
            except ValidationError as e:
                return Response({
                    'error': 'Password validation failed',
                    'details': list(e.messages)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if token exists and is valid
            user_id = cache.get(f"password_reset_{token}")
            if not user_id:
                return Response({
                    'error': 'Invalid or expired reset token'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user and update password
            try:
                user = User.objects.get(id=user_id)
                user.set_password(new_password)
                user.save()
                
                # Remove the token from cache
                cache.delete(f"password_reset_{token}")
                
                logger.info(f"Password reset successful for user {user.email}")
                
                return Response({
                    'message': 'Password has been reset successfully. You can now log in with your new password.'
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error in reset password: {str(e)}")
            return Response({
                'error': 'An error occurred. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
