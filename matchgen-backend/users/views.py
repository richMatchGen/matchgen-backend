from rest_framework import generics, status,viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer,ClubSerializer
from .models import User,Club
from django.contrib.auth import get_user_model


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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "email": user.email,
            "profile_picture": user.profile_picture,
        })

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

    def get_queryset(self):
        # Only allow access to clubs the current user owns
        return self.queryset.filter(user=self.request.user)

    def perform_update(self, serializer):
        # Ensure the user doesn't change ownership accidentally
        serializer.save(user=self.request.user)


class ClubListCreateView(generics.ListCreateAPIView):
    serializer_class = ClubSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return the current user's club(s)
        return Club.objects.filter(user=self.request.user)

    def post(self, request):
        serializer = ClubSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
