from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    ClubDetailView,
    ClubViewSet,
    CreateClubView,
    CustomTokenObtainPairView,
    HealthCheckView,
    LoginView,
    MyClubView,
    RegisterView,
    TestTokenEndpointView,
    UploadLogoView,
    UserDetailView,
    UserListView,
    UserProfileView,
    ClubListView,
    ClubCreateView,
    ClubUpdateView,
    ClubDeleteView,
    TeamManagementView,
    UpdateMemberRoleView,
    RemoveMemberView,
    FeatureAccessView,
    AuditLogView,
    AcceptInviteView,
    PendingInvitesView
)


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


router = DefaultRouter()
router.register(r"clubs", ClubViewSet, basename="club")

urlpatterns = [
    # Health check
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("test-token/", TestTokenEndpointView.as_view(), name="test-token-endpoint"),
    
    # Authentication
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("google/", GoogleLogin.as_view(), name="google_login"),
    
    # User management
    path("me/", UserDetailView.as_view(), name="user-detail"),
    path("all-users/", UserListView.as_view(), name="all-users"),
    
    # Club management
    path("club/", CreateClubView.as_view(), name="club-create"),
    path("club/<int:id>/", ClubDetailView.as_view(), name="club-detail"),
    path("club/upload-logo/", UploadLogoView.as_view(), name="upload-logo"),
    path("my-club/", MyClubView.as_view(), name="my-club"),

    # User Profile
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    
    # Club Management
    path('clubs/', ClubListView.as_view(), name='club_list'),
    path('clubs/create/', ClubCreateView.as_view(), name='club_create'),
    path('clubs/<int:pk>/', ClubDetailView.as_view(), name='club_detail'),
    path('clubs/<int:pk>/update/', ClubUpdateView.as_view(), name='club_update'),
    path('clubs/<int:pk>/delete/', ClubDeleteView.as_view(), name='club_delete'),
    
    # Team Management
    path('team-management/', TeamManagementView.as_view(), name='team_management'),
    path('members/<int:membership_id>/update-role/', UpdateMemberRoleView.as_view(), name='update_member_role'),
    path('members/<int:membership_id>/remove/', RemoveMemberView.as_view(), name='remove_member'),
    
    # Feature Access
    path('feature-access/', FeatureAccessView.as_view(), name='feature_access'),
    
    # Audit Logs
    path('audit-logs/', AuditLogView.as_view(), name='audit_logs'),
    
    # Invitations
    path('accept-invite/', AcceptInviteView.as_view(), name='accept_invite'),
    path('pending-invites/', PendingInvitesView.as_view(), name='pending_invites'),
] + router.urls
