from django.urls import path
from .views import RegisterView, LoginView,UserDetailView,UserListView,ClubViewSet,CreateClubView,ClubDetailView
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

router = DefaultRouter()
router.register(r'clubs', ClubViewSet, basename='club')

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", UserDetailView.as_view(), name="user-detail"),
    path('api/users/google/', GoogleLogin.as_view(), name='google_login'),
    path("all-users/", UserListView.as_view(), name="all-users"),

    # ✅ JWT login & refresh

    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ✅ Club
    path("club/", CreateClubView.as_view(), name="create-club"),
    path('clubs/<int:pk>/', ClubDetailView.as_view(), name='club-detail'),
]
