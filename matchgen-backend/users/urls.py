from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import ObtainTokenView   

from .views import (
    ClubDetailView,
    ClubViewSet,
    CreateClubView,
    LoginView,
    MyClubView,
    RegisterView,
    UserDetailView,
    UserListView,
)


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


router = DefaultRouter()
router.register(r"clubs", ClubViewSet, basename="club")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", UserDetailView.as_view(), name="user-detail"),
    path("api/users/google/", GoogleLogin.as_view(), name="google_login"),
    path("all-users/", UserListView.as_view(), name="all-users"),
    # ✅ JWT login & refresh
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # ✅ Club
    path("club/", CreateClubView.as_view(), name="club-list-create"),
    path("club/<int:id>/", ClubDetailView.as_view(), name="club-detail"),
    path("my-club/", MyClubView.as_view(), name="my-club"),
    path("token/", ObtainTokenView.as_view(), name="token_obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
