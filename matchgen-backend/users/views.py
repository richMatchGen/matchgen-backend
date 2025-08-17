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

User = get_user_model()


class RegisterView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        print("Received Data:", request.data)  # ✅ Log received data

        if not email or not password:
            return Response({"error": "Email and password are required."}, status=400)

        try:
            user = User.objects.create_user(email=email, password=password)
            return Response({"message": "User created successfully!"}, status=201)
        except Exception as e:
            print("Error:", str(e))  # ✅ Log the error in Railway logs
            return Response({"error": str(e)}, status=500)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            print("LoginView - Received data:", request.data)  # Debug log
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                return Response(serializer.validated_data, status=status.HTTP_200_OK)
            else:
                print("LoginView - Validation errors:", serializer.errors)  # Debug log
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print("LoginView - Exception:", str(e))  # Debug log
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListView(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class ClubViewSet(viewsets.ModelViewSet):
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Club.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ClubListView(generics.ListAPIView):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticated]


class ClubDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        # Optional: limit access to the clubs the user created
        return Club.objects.filter(user=self.request.user)


class CreateClubView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ClubSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyClubView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        club = Club.objects.filter(user=request.user).first()
        if not club:
            return Response(
                {"detail": "No club found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = ClubSerializer(club)
        return Response(serializer.data)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        try:
            print("CustomTokenObtainPairView - Received data:", request.data)  # Debug log
            print("CustomTokenObtainPairView - Request headers:", dict(request.headers))  # Debug log
            
            # Check if the request has the right content type
            if request.content_type != 'application/json':
                print("CustomTokenObtainPairView - Wrong content type:", request.content_type)
                return Response(
                    {"error": "Content-Type must be application/json"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            response = super().post(request, *args, **kwargs)
            print("CustomTokenObtainPairView - Response status:", response.status_code)  # Debug log
            return response
        except Exception as e:
            print("CustomTokenObtainPairView - Exception:", str(e))  # Debug log
            import traceback
            print("CustomTokenObtainPairView - Traceback:", traceback.format_exc())  # Debug log
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({"status": "healthy", "message": "Users API is working"}, status=status.HTTP_200_OK)
    
    def post(self, request):
        return Response({"status": "healthy", "message": "Users API POST is working", "data": request.data}, status=status.HTTP_200_OK)


class SimpleTokenView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            print("SimpleTokenView - Received data:", request.data)
            print("SimpleTokenView - Request headers:", dict(request.headers))
            
            # Just return a simple response to test if the endpoint is reachable
            return Response({
                "message": "Simple token endpoint is working",
                "received_data": request.data,
                "content_type": request.content_type
            }, status=status.HTTP_200_OK)
                
        except Exception as e:
            print("SimpleTokenView - Exception:", str(e))
            import traceback
            print("SimpleTokenView - Traceback:", traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestTokenView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            print("TestTokenView - Received data:", request.data)
            print("TestTokenView - Request headers:", dict(request.headers))
            email = request.data.get('email')
            password = request.data.get('password')
            
            if not email or not password:
                return Response({"error": "Email and password required"}, status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
                refresh = RefreshToken.for_user(user)
                return Response({
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        'id': user.id,
                        'email': user.email,
                        'profile_picture': user.profile_picture
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
                
        except Exception as e:
            print("TestTokenView - Exception:", str(e))
            import traceback
            print("TestTokenView - Traceback:", traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
