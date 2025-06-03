import csv
import io

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import Club

from .models import Match, Player
from .serializers import FixturesSerializer, MatchSerializer, PlayerSerializer


class MatchListView(ListAPIView):
    serializer_class = FixturesSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Match.objects.filter(club__user=user).order_by("date")


class MatchListCreateView(generics.ListCreateAPIView):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
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
        if isinstance(data, list):
            serializer = self.get_serializer(data=data, many=True)
        else:
            serializer = self.get_serializer(data=data)

        serializer.is_valid(raise_exception=True)

        try:
            club = Club.objects.get(user=request.user)
        except Club.DoesNotExist:
            return Response(
                {"error": "Club not found for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        if isinstance(data, list):
            serializer = self.get_serializer(data=data, many=True)
        else:
            serializer = self.get_serializer(data=data)

        serializer.is_valid(raise_exception=True)

        try:
            club = Club.objects.get(user=request.user)
        except Club.DoesNotExist:
            return Response(
                {"error": "Club not found for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(club=club)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LastMatchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            club = user.clubs.first()

            if not club:
                return Response(
                    {"detail": "User is not associated with any clubs."},
                    status=status.HTTP_200_OK,
                )

            today = timezone.now().date()

            last_match = (
                Match.objects.filter(club=club)
                .filter(date__lt=today)  # ✅ only matches before today
                .order_by("-date", "-time_start")  # latest first
                .first()
            )

            if last_match:
                return Response(MatchSerializer(last_match).data)

            return Response(
                {"detail": "No past matches found."}, status=status.HTTP_200_OK
            )

        except Exception as e:
            import traceback

            print(traceback.format_exc())
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MatchdayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            club = user.clubs.first()

            if not club:
                return Response(
                    {"detail": "User is not associated with any clubs."},
                    status=status.HTTP_200_OK,
                )

            now = timezone.now()

            next_match = (
                Match.objects.filter(club=club)
                .filter(date__gte=now.date())  # upcoming matches (today or later)
                .order_by("date", "time_start")  # soonest first
                .first()
            )

            if next_match:
                return Response(MatchSerializer(next_match).data)

            return Response(
                {"detail": "No upcoming matches found."}, status=status.HTTP_200_OK
            )

        except Exception as e:
            import traceback

            print(traceback.format_exc())
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpcomingMatchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            club = user.clubs.first()

            if not club:
                return Response(
                    {"detail": "User is not associated with any clubs."},
                    status=status.HTTP_200_OK,
                )

            now = timezone.now()

            upcoming_matches = (
                Match.objects.filter(club=club)
                .filter(date__gte=now.date())
                .order_by("date", "time_start")
            )

            if upcoming_matches.count() > 1:
                second_match = upcoming_matches[1]
                return Response(MatchSerializer(second_match).data)
            elif upcoming_matches.exists():
                return Response(
                    {"detail": "Only one upcoming match found."},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"detail": "No upcoming matches found."}, status=status.HTTP_200_OK
                )

        except Exception as e:
            import traceback

            print(traceback.format_exc())
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
