import csv
import io
import logging

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

logger = logging.getLogger(__name__)


class MatchListView(ListAPIView):
    """List all matches for the authenticated user."""
    serializer_class = FixturesSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Match.objects.filter(club__user=user).order_by("date")


class MatchListCreateView(generics.ListCreateAPIView):
    """List and create matches."""
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Match.objects.filter(club__user=self.request.user)

    def perform_create(self, serializer):
        try:
            club = Club.objects.get(user=self.request.user)
            match = serializer.save(club=club)
            logger.info(f"Match created: {match.opponent} vs {match.club.name} on {match.date}")
        except Club.DoesNotExist:
            logger.error(f"No club found for user: {self.request.user.email}")
            raise
        except Exception as e:
            logger.error(f"Error creating match: {str(e)}", exc_info=True)
            raise

    def create(self, request, *args, **kwargs):
        try:
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
                    {"error": "Club not found for this user. Please create a club first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer.save(club=club)
            logger.info(f"Match(es) created successfully for user: {request.user.email}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error in match creation: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while creating the match(es)."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BulkUploadMatchesView(APIView):
    """Bulk upload matches from CSV file."""
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            csv_file = request.FILES.get("file")
            if not csv_file:
                return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

            if not csv_file.name.endswith('.csv'):
                return Response({"error": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)

            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found for this user. Please create a club first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            decoded_file = csv_file.read().decode("utf-8")
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            matches_created = []
            errors = []

            for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                try:
                    match = Match.objects.create(
                        club=club,
                        opponent=row.get("opponent", ""),
                        date=row.get("date"),
                        location=row.get("location", ""),
                        venue=row.get("venue", ""),
                        time_start=row.get("time_start", ""),
                        match_type=row.get("match_type", "League"),
                    )
                    matches_created.append(match.id)
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    logger.warning(f"Error processing CSV row {row_num}: {str(e)}")

            logger.info(f"Bulk upload completed. {len(matches_created)} matches created, {len(errors)} errors")
            
            response_data = {"created": matches_created}
            if errors:
                response_data["errors"] = errors

            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Bulk upload error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred during bulk upload."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PlayerListCreateView(generics.ListCreateAPIView):
    """List and create players."""
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Player.objects.filter(club__user=self.request.user)

    def perform_create(self, serializer):
        try:
            club = Club.objects.get(user=self.request.user)
            player = serializer.save(club=club)
            logger.info(f"Player created: {player.name} for club {club.name}")
        except Club.DoesNotExist:
            logger.error(f"No club found for user: {self.request.user.email}")
            raise
        except Exception as e:
            logger.error(f"Error creating player: {str(e)}", exc_info=True)
            raise

    def create(self, request, *args, **kwargs):
        try:
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
                    {"error": "Club not found for this user. Please create a club first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer.save(club=club)
            logger.info(f"Player(s) created successfully for user: {request.user.email}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error in player creation: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while creating the player(s)."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LastMatchView(APIView):
    """Get the last completed match for the user's club."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            club = user.clubs.first()

            if not club:
                return Response(
                    {"detail": "User is not associated with any clubs."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            today = timezone.now().date()

            last_match = (
                Match.objects.filter(club=club)
                .filter(date__lt=today)  # only matches before today
                .order_by("-date", "-time_start")  # latest first
                .first()
            )

            if last_match:
                logger.info(f"Last match retrieved for club {club.name}: {last_match.opponent}")
                return Response(MatchSerializer(last_match).data)

            return Response(
                {"detail": "No past matches found."}, status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error fetching last match: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching the last match."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MatchdayView(APIView):
    """Get the next upcoming match for the user's club."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            club = user.clubs.first()

            if not club:
                return Response(
                    {"detail": "User is not associated with any clubs."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            now = timezone.now()

            next_match = (
                Match.objects.filter(club=club)
                .filter(date__gte=now.date())  # upcoming matches (today or later)
                .order_by("date", "time_start")  # soonest first
                .first()
            )

            if next_match:
                logger.info(f"Next match retrieved for club {club.name}: {next_match.opponent}")
                return Response(MatchSerializer(next_match).data)

            return Response(
                {"detail": "No upcoming matches found."}, status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error fetching next match: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching the next match."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpcomingMatchView(APIView):
    """Get the second upcoming match for the user's club."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            club = user.clubs.first()

            if not club:
                return Response(
                    {"detail": "User is not associated with any clubs."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            now = timezone.now()

            upcoming_matches = (
                Match.objects.filter(club=club)
                .filter(date__gte=now.date())
                .order_by("date", "time_start")
            )

            if upcoming_matches.count() > 1:
                second_match = upcoming_matches[1]
                logger.info(f"Second upcoming match retrieved for club {club.name}: {second_match.opponent}")
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
            logger.error(f"Error fetching second upcoming match: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching the upcoming match."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
