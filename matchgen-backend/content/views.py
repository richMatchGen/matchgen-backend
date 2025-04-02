from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Match, Player
from users.models import Club
from .serializers import MatchSerializer,PlayerSerializer
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.views import APIView
import csv, io

class MatchListCreateView(generics.ListCreateAPIView):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        print('SelfUser')
        print(self.request.user)
        return Match.objects.filter(club__user=self.request.user)
        
    def perform_create(self, serializer):
        try:
            club = Club.objects.get(user=self.request.user)
            serializer.save(club=club)
        except Exception as e:
            import logging
            logging.error(f"Error assigning club: {e}")
            raise

    def create(self, request, *args, **kwargs):
        data = request.data
        print('Data')
        print(data)

        if isinstance(data, list):
            serializer = self.get_serializer(data=data, many=True)
        else:
            serializer = self.get_serializer(data=data)

        serializer.is_valid(raise_exception=True)

        try:
            club = Club.objects.get(user=request.user)
        except Club.DoesNotExist:
            return Response({"error": "Club not found for this user."}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(club=club)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BulkUploadMatchesView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        csv_file = request.FILES.get("file")
        if not csv_file:
            return Response({"error": "No file uploaded."}, status=400)

        decoded_file = csv_file.read().decode("utf-8")
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        matches_created = []
        for row in reader:
            match = Match.objects.create(
                club=request.user.clubs.first(),  # or selected via frontend
                opponent=row.get("opponent"),
                date=row.get("date"),
                location=row.get("location"),
                home=row.get("home") in ["true", "1", "yes"],
                notes=row.get("notes", ""),
            )
            matches_created.append(match.id)

        return Response({"created": matches_created}, status=status.HTTP_201_CREATED)
    


class PlayerListCreateView(generics.ListCreateAPIView):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Player.objects.filter(club__user=self.request.user)
        
    def perform_create(self, serializer):
        try:
            club = Club.objects.get(user=self.request.user)
            serializer.save(club=club)
        except Exception as e:
            import logging
            logging.error(f"Error assigning club: {e}")
            raise

    def create(self, request, *args, **kwargs):
        data = request.data
        print('Data')
        print(data)

        if isinstance(data, list):
            serializer = self.get_serializer(data=data, many=True)
        else:
            serializer = self.get_serializer(data=data)

        serializer.is_valid(raise_exception=True)

        try:
            club = Club.objects.get(user=request.user)
        except Club.DoesNotExist:
            return Response({"error": "Club not found for this user."}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(club=club)

        return Response(serializer.data, status=status.HTTP_201_CREATED)     
    

class LastMatchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Make sure the user is linked to a club
            user = request.user
            club = getattr(user, "id", None)

            if not club:
                return Response({"detail": "User is not associated with a club."}, status=status.HTTP_200_OK)

            last_match = (
                Match.objects.filter(club=id)
                .order_by("-date", "-time_start")
                .first()
            )

            if last_match:
                serialized = MatchSerializer(last_match).data
                return Response(serialized)

            return Response({"detail": "No matches found."}, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            print(traceback.format_exc())  # This prints full error to Railway logs
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)