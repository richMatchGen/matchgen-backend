import csv
import io
import logging
import time

from django.utils import timezone
from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import Club

from .models import Match, Player
from .serializers import FixturesSerializer, MatchSerializer, PlayerSerializer

logger = logging.getLogger(__name__)

# Simple rate limiting for debugging
class RateLimitMixin:
    def check_rate_limit(self, user_id, endpoint, limit_seconds=5):
        """Simple rate limiting to prevent excessive calls."""
        cache_key = f"rate_limit_{endpoint}_{user_id}"
        last_call = cache.get(cache_key)
        current_time = timezone.now()
        
        if last_call:
            time_diff = (current_time - last_call).total_seconds()
            if time_diff < limit_seconds:
                logger.warning(f"Rate limit exceeded for user {user_id} on {endpoint}. Time since last call: {time_diff}s")
                return False
        
        cache.set(cache_key, current_time, 60)  # Cache for 1 minute
        return True


class MatchListView(ListAPIView, RateLimitMixin):
    """List all matches for the authenticated user."""
    serializer_class = FixturesSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Add request tracking
        logger.info(f"MatchListView called by user {user.email} at {timezone.now()}")
        logger.info(f"Request headers: {dict(self.request.headers)}")
        
        # Check rate limiting
        if not self.check_rate_limit(user.id, "matches", limit_seconds=30):  # Increased from 3 to 30 seconds
            logger.warning(f"Rate limit exceeded for matches endpoint - user {user.email}")
            # Return empty queryset instead of raising error to avoid breaking frontend
            return Match.objects.none()
        
        matches = Match.objects.filter(club__user=user).order_by("date")
        logger.info(f"Found {matches.count()} matches for user {user.email}")
        return matches


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


class MatchDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific match."""
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Match.objects.filter(club__user=self.request.user)

    def perform_update(self, serializer):
        try:
            match = serializer.save()
            logger.info(f"Match updated: {match.opponent} vs {match.club.name} on {match.date}")
        except Exception as e:
            logger.error(f"Error updating match: {str(e)}", exc_info=True)
            raise

    def perform_destroy(self, instance):
        try:
            match_info = f"{instance.opponent} vs {instance.club.name} on {instance.date}"
            instance.delete()
            logger.info(f"Match deleted: {match_info}")
        except Exception as e:
            logger.error(f"Error deleting match: {str(e)}", exc_info=True)
            raise


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


class PlayerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific player."""
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Player.objects.filter(club__user=self.request.user)

    def perform_update(self, serializer):
        try:
            club = Club.objects.get(user=self.request.user)
            serializer.save(club=club)
            logger.info(f"Player updated: {serializer.instance.name} for club {club.name}")
        except Club.DoesNotExist:
            logger.error(f"No club found for user: {self.request.user.email}")
            raise

    def perform_destroy(self, instance):
        player_name = instance.name
        instance.delete()
        logger.info(f"Player deleted: {player_name}")


class LastMatchView(APIView):
    """Get the last completed match for the user's club."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            
            # Try to get club with error handling for migration issues
            try:
                club = user.clubs.first()
            except Exception as club_error:
                logger.error(f"Error accessing user clubs: {str(club_error)}", exc_info=True)
                # Fallback: try direct Club query
                try:
                    club = Club.objects.filter(user=user).first()
                except Exception as fallback_error:
                    logger.error(f"Fallback club query also failed: {str(fallback_error)}", exc_info=True)
                    return Response(
                        {"detail": "Database migration in progress. Please try again later."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

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
            
            # Try to get club with error handling for migration issues
            try:
                club = user.clubs.first()
            except Exception as club_error:
                logger.error(f"Error accessing user clubs: {str(club_error)}", exc_info=True)
                # Fallback: try direct Club query
                try:
                    club = Club.objects.filter(user=user).first()
                except Exception as fallback_error:
                    logger.error(f"Fallback club query also failed: {str(fallback_error)}", exc_info=True)
                    return Response(
                        {"detail": "Database migration in progress. Please try again later."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

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
            
            # Try to get club with error handling for migration issues
            try:
                club = user.clubs.first()
            except Exception as club_error:
                logger.error(f"Error accessing user clubs: {str(club_error)}", exc_info=True)
                # Fallback: try direct Club query
                try:
                    club = Club.objects.filter(user=user).first()
                except Exception as fallback_error:
                    logger.error(f"Fallback club query also failed: {str(fallback_error)}", exc_info=True)
                    return Response(
                        {"detail": "Database migration in progress. Please try again later."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

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


class SubstitutionPlayersView(APIView):
    """Get players for substitution dropdowns."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            
            # Try to get club with error handling for migration issues
            try:
                club = user.clubs.first()
            except Exception as club_error:
                logger.error(f"Error accessing user clubs: {str(club_error)}", exc_info=True)
                # Fallback: try direct Club query
                try:
                    club = Club.objects.filter(user=user).first()
                except Exception as fallback_error:
                    logger.error(f"Fallback club query also failed: {str(fallback_error)}", exc_info=True)
                    return Response(
                        {"detail": "Database migration in progress. Please try again later."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

            if not club:
                return Response(
                    {"detail": "User is not associated with any clubs."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            players = Player.objects.filter(club=club).order_by('name')
            
            # Return simplified player data for dropdowns
            player_data = [
                {
                    "id": player.id,
                    "name": player.name,
                    "squad_no": player.squad_no,
                    "position": player.position
                }
                for player in players
            ]

            logger.info(f"Retrieved {len(player_data)} players for substitution dropdowns for club {club.name}")
            return Response(player_data)

        except Exception as e:
            logger.error(f"Error fetching players for substitution: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching players."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OpponentLogoUploadView(APIView):
    """Upload opponent logo for matches."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        try:
            logo_file = request.FILES.get('logo')
            if not logo_file:
                return Response(
                    {"error": "No logo file provided."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Upload to Cloudinary
            try:
                import cloudinary
                import cloudinary.uploader
                from django.conf import settings
                
                upload_result = cloudinary.uploader.upload(
                    logo_file,
                    folder="opponent_logos",
                    public_id=f"opponent_{request.user.id}_{int(time.time())}",
                    overwrite=True,
                    resource_type="image",
                    tags=["Logo"]
                )
                
                logo_url = upload_result['secure_url']
                logger.info(f"Opponent logo uploaded to Cloudinary: {logo_url}")
                
                # Add to media manager
                try:
                    from users.models import Club
                    from graphicpack.models import MediaItem
                    
                    club = Club.objects.get(user=request.user)
                    
                    # Get image dimensions
                    width = None
                    height = None
                    try:
                        from PIL import Image
                        img = Image.open(logo_file)
                        width, height = img.size
                    except Exception as e:
                        logger.warning(f"Could not get image dimensions: {str(e)}")
                    
                    # Create MediaItem record
                    media_item = MediaItem.objects.create(
                        club=club,
                        title=f"Opponent Logo - {logo_file.name}",
                        description="Opponent logo uploaded during match creation",
                        media_type='opponent_logo',
                        category='logos',
                        file_url=logo_url,
                        file_name=logo_file.name,
                        file_size=logo_file.size,
                        file_type=logo_file.content_type,
                        width=width,
                        height=height,
                        cloudinary_public_id=upload_result['public_id'],
                        cloudinary_folder=upload_result.get('folder', ''),
                        tags=['opponent', 'logo', 'match']
                    )
                    
                    logger.info(f"Added opponent logo to media manager: {media_item.id}")
                    
                except Exception as media_error:
                    logger.warning(f"Failed to add opponent logo to media manager: {str(media_error)}")
                    # Don't fail the upload if media manager addition fails
                
                return Response({
                    "logo_url": logo_url,
                    "message": "Opponent logo uploaded successfully"
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Opponent logo upload failed: {str(e)}")
                return Response(
                    {"error": "Failed to upload opponent logo. Please try again."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error in opponent logo upload: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while uploading the logo."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PlayerPhotoUploadView(APIView):
    """Upload player photo."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        try:
            photo_file = request.FILES.get('photo')
            if not photo_file:
                return Response(
                    {"error": "No photo file provided."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Upload to Cloudinary
            try:
                import cloudinary
                import cloudinary.uploader
                from django.conf import settings
                
                upload_result = cloudinary.uploader.upload(
                    photo_file,
                    folder="player_photos",
                    public_id=f"player_{request.user.id}_{int(time.time())}",
                    overwrite=True,
                    resource_type="image"
                )
                
                photo_url = upload_result['secure_url']
                logger.info(f"Player photo uploaded to Cloudinary: {photo_url}")
                
                # Add to media manager
                try:
                    from users.models import Club
                    from graphicpack.models import MediaItem
                    
                    club = Club.objects.get(user=request.user)
                    
                    # Get image dimensions
                    width = None
                    height = None
                    try:
                        from PIL import Image
                        img = Image.open(photo_file)
                        width, height = img.size
                    except Exception as e:
                        logger.warning(f"Could not get image dimensions: {str(e)}")
                    
                    # Create MediaItem record
                    media_item = MediaItem.objects.create(
                        club=club,
                        title=f"Player Photo - {photo_file.name}",
                        description="Player photo uploaded during player creation",
                        media_type='player_photo',
                        category='players',
                        file_url=photo_url,
                        file_name=photo_file.name,
                        file_size=photo_file.size,
                        file_type=photo_file.content_type,
                        width=width,
                        height=height,
                        cloudinary_public_id=upload_result['public_id'],
                        cloudinary_folder=upload_result.get('folder', ''),
                        tags=['player', 'photo', 'squad']
                    )
                    
                    logger.info(f"Added player photo to media manager: {media_item.id}")
                    
                except Exception as media_error:
                    logger.warning(f"Failed to add player photo to media manager: {str(media_error)}")
                    # Don't fail the upload if media manager addition fails
                
                return Response({
                    "photo_url": photo_url,
                    "message": "Player photo uploaded successfully"
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Player photo upload failed: {str(e)}")
                return Response(
                    {"error": "Failed to upload player photo. Please try again."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error in player photo upload: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while uploading the photo."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
