import logging
import base64
import requests
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
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404

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


class TeamManagementView(APIView):
    """View for managing team members and roles"""
    permission_classes = [IsClubMember]
    
    def get(self, request):
        """Get team management data"""
        club_id = request.query_params.get('club_id')
        if not club_id:
            return Response({"error": "Club ID is required"}, status=400)
        
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=404)
        
        # Check if user can manage members
        if not can_manage_team_members(request.user, club):
            return Response({"error": "You don't have permission to manage team members"}, status=403)
        
        members = ClubMembership.objects.filter(club=club).select_related('user', 'role', 'invited_by')
        available_roles = UserRole.objects.all()
        
        data = {
            'members': ClubMembershipSerializer(members, many=True).data,
            'available_roles': UserRoleSerializer(available_roles, many=True).data,
            'can_manage_members': can_manage_team_members(request.user, club),
            'can_manage_billing': can_manage_billing(request.user, club),
        }
        
        return Response(TeamManagementSerializer(data).data)
    
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
    permission_classes = [IsClubMember]
    
    def get(self, request):
        """Get feature access information for a club"""
        club_id = request.query_params.get('club_id')
        if not club_id:
            return Response({"error": "Club ID is required"}, status=400)
        
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=404)
        
        available_features = FeaturePermission.get_available_features(club)
        
        # Check access to specific features
        feature_access = {}
        all_features = Feature.objects.filter(is_active=True)
        for feature in all_features:
            feature_access[feature.code] = FeaturePermission.has_feature_access(request.user, club, feature.code)
        
        data = {
            'available_features': available_features,
            'subscription_tier': club.subscription_tier,
            'subscription_active': club.subscription_active,
            'feature_access': feature_access
        }
        
        return Response(FeatureAccessSerializer(data).data)


class FeaturesView(APIView):
    """View for listing all available features"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all available features"""
        features = Feature.objects.filter(is_active=True)
        return Response(FeatureSerializer(features, many=True).data)


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
