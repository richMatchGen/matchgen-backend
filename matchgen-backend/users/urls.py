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
] + router.urls
