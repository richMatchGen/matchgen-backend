from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from .models import ClubMembership, UserRole, Feature, SubscriptionTierFeature, AuditLog, Club


class RoleBasedPermission:
    """Base class for role-based permissions"""
    
    def __init__(self, required_roles=None, allow_owner=True):
        self.required_roles = required_roles or []
        self.allow_owner = allow_owner
    
    def has_permission(self, user, club):
        """Check if user has permission for the given club"""
        if not user.is_authenticated:
            return False
        
        try:
            membership = ClubMembership.objects.get(user=user, club=club, status='active')
            role_name = membership.role.name
            
            # Owner always has access
            if self.allow_owner and role_name == 'owner':
                return True
            
            # Check if user's role is in required roles
            if role_name in self.required_roles:
                return True
                
            return False
            
        except ClubMembership.DoesNotExist:
            return False


class FeaturePermission:
    """Check if user has access to specific features based on subscription tier"""
    
    @staticmethod
    def has_feature_access(user, club, feature_code):
        """Check if user's club has access to a specific feature"""
        if not user.is_authenticated:
            return False
        
        # Check if club subscription is active
        if not club.subscription_active:
            return False
        
        # Check if feature is available for the subscription tier
        try:
            feature = Feature.objects.get(code=feature_code, is_active=True)
            SubscriptionTierFeature.objects.get(
                subscription_tier=club.subscription_tier,
                feature=feature
            )
            return True
        except (Feature.DoesNotExist, SubscriptionTierFeature.DoesNotExist):
            return False
    
    @staticmethod
    def get_available_features(club):
        """Get all available features for a club's subscription tier"""
        if not club.subscription_active:
            return []
        
        return SubscriptionTierFeature.objects.filter(
            subscription_tier=club.subscription_tier,
            feature__is_active=True
        ).values_list('feature__code', flat=True)


class ClubAccessMixin:
    """Mixin to ensure user has access to the club"""
    
    def get_club(self, request):
        """Get club from request and verify access"""
        club_id = request.data.get('club_id') or request.query_params.get('club_id')
        if not club_id:
            raise DRFPermissionDenied("Club ID is required")
        
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            raise Http404("Club not found")
        
        # Check if user has any role in this club
        if not ClubMembership.objects.filter(
            user=request.user, 
            club=club, 
            status='active'
        ).exists():
            raise DRFPermissionDenied("You don't have access to this club")
        
        return club


class AuditLogger:
    """Utility class for logging audit events"""
    
    @staticmethod
    def log_event(user, club, action, details=None, request=None):
        """Log an audit event"""
        audit_data = {
            'user': user,
            'club': club,
            'action': action,
            'details': details or {},
        }
        
        if request:
            audit_data['ip_address'] = self._get_client_ip(request)
            audit_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        AuditLog.objects.create(**audit_data)
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# Permission classes for DRF
class IsClubMember(permissions.BasePermission):
    """Allow access only to club members"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        club_id = request.data.get('club_id') or request.query_params.get('club_id')
        if not club_id:
            return False
        
        # Check for active membership first
        if ClubMembership.objects.filter(
            user=request.user,
            club_id=club_id,
            status='active'
        ).exists():
            return True
        
        # Fallback: Check for direct club ownership (legacy system)
        try:
            club = Club.objects.get(id=club_id, user=request.user)
            return True
        except Club.DoesNotExist:
            return False


class HasRolePermission(permissions.BasePermission):
    """Allow access based on user role"""
    
    def __init__(self, required_roles=None, allow_owner=True):
        self.required_roles = required_roles or []
        self.allow_owner = allow_owner
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        club_id = request.data.get('club_id') or request.query_params.get('club_id')
        if not club_id:
            return False
        
        try:
            membership = ClubMembership.objects.get(
                user=request.user,
                club_id=club_id,
                status='active'
            )
            role_name = membership.role.name
            
            if self.allow_owner and role_name == 'owner':
                return True
            
            return role_name in self.required_roles
            
        except ClubMembership.DoesNotExist:
            return False


class HasFeaturePermission(permissions.BasePermission):
    """Allow access based on feature availability"""
    
    def __init__(self, feature_code):
        self.feature_code = feature_code
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        club_id = request.data.get('club_id') or request.query_params.get('club_id')
        if not club_id:
            return False
        
        try:
            club = Club.objects.get(id=club_id)
            return FeaturePermission.has_feature_access(request.user, club, self.feature_code)
        except Club.DoesNotExist:
            return False


# Utility functions
def get_user_role_in_club(user, club):
    """Get user's role in a specific club"""
    try:
        membership = ClubMembership.objects.get(user=user, club=club, status='active')
        return membership.role.name
    except ClubMembership.DoesNotExist:
        return None


def can_manage_team_members(user, club):
    """Check if user can manage team members (Owner or Admin)"""
    # Check direct ownership (legacy system)
    if club.user == user:
        return True
    
    # Check RBAC membership
    role = get_user_role_in_club(user, club)
    return role in ['owner', 'admin']


def can_manage_billing(user, club):
    """Check if user can manage billing (Owner only)"""
    # Check direct ownership (legacy system)
    if club.user == user:
        return True
    
    # Check RBAC membership
    role = get_user_role_in_club(user, club)
    return role == 'owner'


def can_create_posts(user, club):
    """Check if user can create posts (Owner, Admin, Editor)"""
    # Check direct ownership (legacy system)
    if club.user == user:
        return True
    
    # Check RBAC membership
    role = get_user_role_in_club(user, club)
    return role in ['owner', 'admin', 'editor']


def can_view_only(user, club):
    """Check if user can only view (Viewer)"""
    # Check direct ownership (legacy system) - owners can do more than just view
    if club.user == user:
        return False
    
    # Check RBAC membership
    role = get_user_role_in_club(user, club)
    return role == 'viewer'
