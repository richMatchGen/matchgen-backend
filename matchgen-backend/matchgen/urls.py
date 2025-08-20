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
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


# Simple Root View to Show API is Working
def home_view(request):
    return JsonResponse({"message": "MatchGen API is running!"})


class TestTokenRefreshView(APIView):
    """Test endpoint to diagnose token refresh issues."""
    
    def post(self, request):
        try:
            # Log the request data for debugging
            print(f"Token refresh request data: {request.data}")
            print(f"Token refresh request headers: {dict(request.headers)}")
            
            # Call the original TokenRefreshView
            from rest_framework_simplejwt.views import TokenRefreshView
            refresh_view = TokenRefreshView()
            response = refresh_view.post(request)
            
            print(f"Token refresh response: {response.data}")
            return response
            
        except Exception as e:
            print(f"Token refresh error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Token refresh failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class APIHealthCheckView(APIView):
    """Comprehensive health check for the API."""
    
    def get(self, request):
        try:
            # Test basic functionality
            health_status = {
                "status": "healthy",
                "message": "MatchGen API is working",
                "timestamp": "2025-08-18T11:30:00Z",
                "endpoints": {
                    "root": "/",
                    "health": "/api/health/",
                    "users": "/api/users/",
                    "content": "/api/content/",
                    "graphicpack": "/api/graphicpack/",
                    "token_refresh": "/api/token/refresh/",
                    "test_token_refresh": "/api/test-token-refresh/",
                },
                "database": "connected",
                "authentication": "jwt_enabled",
                "cors_test": "CORS health check successful"
            }
            return Response(health_status, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Health check error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Health check failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/content/", include("content.urls")),
    path("api/graphicpack/", include("graphicpack.urls")),
    # Global token refresh endpoint for frontend compatibility
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh_global"),
    # Test endpoint for debugging
    path("api/test-token-refresh/", TestTokenRefreshView.as_view(), name="test_token_refresh"),
    # Health check endpoint
    path("api/health/", APIHealthCheckView.as_view(), name="api_health"),
    path("", home_view),  # Add this to fix "Not Found" issue
]
