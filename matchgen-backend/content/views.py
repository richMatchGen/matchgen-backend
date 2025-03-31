from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Match
from users.models import Club
from .serializers import MatchSerializer
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.views import APIView
import csv, io

class MatchListCreateView(generics.ListCreateAPIView):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Match.objects.filter(club__user=self.request.user)
    
    def perform_create(self, serializer):
        # Auto-assign club based on the current logged-in user
        club = Club.objects.get(user=self.request.user)
        serializer.save(club=club)

    def create(self, request, *args, **kwargs):
        # Handle both single and bulk upload
        data = request.data
        if isinstance(data, list):
            serializer = self.get_serializer(data=data, many=True)
        else:
            serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
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