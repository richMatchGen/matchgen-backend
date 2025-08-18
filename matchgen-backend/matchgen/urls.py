"""
URL configuration for matchgen project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView


# Simple Root View to Show API is Working
def home_view(request):
    return JsonResponse({"message": "MatchGen API is running!"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/content/", include("content.urls")),
    path("api/graphicpack/", include("graphicpack.urls")),
    # Global token refresh endpoint for frontend compatibility
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh_global"),
    path("", home_view),  # Add this to fix "Not Found" issue
]
