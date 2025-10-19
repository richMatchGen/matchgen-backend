import csv
import io
import logging
import time
import requests
import re
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

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


class FAFulltimeScraperView(APIView):
    """Scrape fixtures from FA Fulltime website."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            fa_url = request.data.get('fa_url')
            if not fa_url:
                return Response(
                    {"error": "FA Fulltime URL is required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate URL format
            if 'fulltime.thefa.com' not in fa_url:
                return Response(
                    {"error": "Please provide a valid FA Fulltime URL."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ensure URL has proper format
            if not fa_url.startswith('http'):
                fa_url = 'https://' + fa_url
                logger.info(f"Added https protocol to URL: {fa_url}")
            
            # Log the URL being accessed for debugging
            logger.info(f"FA Fulltime scraper requested for URL: {fa_url}")

            # Quick connectivity check to prevent worker timeout
            try:
                logger.info("Performing quick connectivity check...")
                test_response = requests.head(fa_url, timeout=5)
                logger.info(f"Connectivity check passed: {test_response.status_code}")
            except Exception as e:
                logger.warning(f"Connectivity check failed: {str(e)}")
                return Response(
                    {
                        "error": "FA Fulltime website is not accessible. This could be due to network issues, the website being down, or anti-bot protection.",
                        "suggestion": "Please try using the CSV upload method instead, or try again later.",
                        "test_endpoint": "Use /api/content/fixtures/import/fa-fulltime/test/ to check URL accessibility"
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found for this user. Please create a club first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Scrape fixtures from FA Fulltime with timeout protection
            logger.info(f"Starting FA scraper for URL: {fa_url}")
            
            try:
                fixtures_data = self.scrape_fa_fixtures(fa_url)
            except Exception as e:
                logger.error(f"FA scraper failed with exception: {str(e)}")
                return Response(
                    {
                        "error": "FA Fulltime scraping failed due to connection issues. The FA website may be temporarily unavailable or blocking requests.",
                        "suggestion": "Please try using the CSV upload method instead, or try again later when the FA website is accessible.",
                        "alternative": "You can also use the test endpoint to check URL accessibility first."
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            
            if not fixtures_data:
                return Response(
                    {
                        "error": "No fixtures found on the provided FA Fulltime page. This could be due to: 1) The page structure has changed, 2) No fixtures are currently available, 3) The URL format is incorrect, or 4) The page requires authentication.",
                        "suggestion": "Please try using the CSV upload method instead, or verify the FA Fulltime URL is correct and accessible.",
                        "test_endpoint": "Use /api/content/fixtures/import/fa-fulltime/test/ to check URL accessibility"
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Create matches
            matches_created = []
            errors = []

            for fixture in fixtures_data:
                try:
                    match = Match.objects.create(
                        club=club,
                        opponent=fixture.get('opponent', ''),
                        date=fixture.get('date'),
                        location=fixture.get('location', ''),
                        venue=fixture.get('venue', ''),
                        time_start=fixture.get('time_start', ''),
                        match_type=fixture.get('match_type', 'League'),
                        home_away=fixture.get('home_away', 'HOME')
                    )
                    matches_created.append(match.id)
                except Exception as e:
                    errors.append(f"Error creating match: {str(e)}")
                    logger.warning(f"Error creating match from FA data: {str(e)}")

            logger.info(f"FA scraper completed. {len(matches_created)} matches created, {len(errors)} errors")
            
            response_data = {
                "created": matches_created,
                "total_found": len(fixtures_data),
                "message": f"Successfully imported {len(matches_created)} fixtures from FA Fulltime"
            }
            if errors:
                response_data["errors"] = errors

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"FA scraper error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while scraping FA fixtures."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def scrape_fa_fixtures(self, url):
        """Scrape fixture data from FA Fulltime website."""
        try:
            # Enhanced headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            # Try with session for better connection handling
            session = requests.Session()
            session.headers.update(headers)
            
            # Reduced timeout and retry logic to prevent worker timeout
            max_retries = 2  # Reduced from 3
            timeout_seconds = 15  # Reduced from 60 to prevent worker timeout
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempting to fetch FA page (attempt {attempt + 1}/{max_retries}): {url}")
                    response = session.get(url, timeout=timeout_seconds, allow_redirects=True)
                    response.raise_for_status()
                    break
                except requests.exceptions.Timeout:
                    if attempt == max_retries - 1:
                        logger.error(f"Timeout after {max_retries} attempts for URL: {url}")
                        return []
                    logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                    time.sleep(1)  # Reduced backoff time
                except requests.exceptions.ConnectionError:
                    if attempt == max_retries - 1:
                        logger.error(f"Connection error after {max_retries} attempts for URL: {url}")
                        return []
                    logger.warning(f"Connection error on attempt {attempt + 1}, retrying...")
                    time.sleep(1)  # Reduced backoff time
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request error: {str(e)}")
                    return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            fixtures = []
            
            # Enhanced fixture detection - look for more patterns
            logger.info("Parsing FA page content...")
            
            # Method 1: Look for fixture tables with various class names
            fixture_tables = soup.find_all('table', class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['fixture', 'result', 'match', 'game', 'schedule']
            ))
            
            # Method 2: Look for divs containing fixture information
            fixture_divs = soup.find_all('div', class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['fixture', 'result', 'match', 'game', 'schedule']
            ))
            
            # Method 3: Look for any table that might contain fixture data
            all_tables = soup.find_all('table')
            
            for table in fixture_tables + all_tables:
                rows = table.find_all('tr')
                if len(rows) > 1:  # Has header and data rows
                    for row in rows[1:]:  # Skip header row
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:  # At least date and opponent
                            fixture_data = self.parse_fixture_row(cells)
                            if fixture_data:
                                fixtures.append(fixture_data)
                                logger.info(f"Found fixture: {fixture_data.get('opponent', 'Unknown')} on {fixture_data.get('date', 'Unknown')}")
            
            # Method 4: Look for fixture lists
            if not fixtures:
                fixture_lists = soup.find_all(['ul', 'ol'], class_=lambda x: x and any(
                    keyword in x.lower() for keyword in ['fixture', 'result', 'match', 'game', 'schedule']
                ))
                for fixture_list in fixture_lists:
                    items = fixture_list.find_all('li')
                    for item in items:
                        fixture_data = self.parse_fixture_text(item.get_text())
                        if fixture_data:
                            fixtures.append(fixture_data)
            
            # Method 5: Look for any text that might contain fixture information
            if not fixtures:
                # Look for common fixture patterns in the page text
                page_text = soup.get_text()
                fixture_patterns = [
                    r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+(.+?)\s+vs\s+(.+)',
                    r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+(.+?)\s+v\s+(.+)',
                    r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+(.+?)\s+@\s+(.+)',
                ]
                
                for pattern in fixture_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    for match in matches:
                        fixture_data = self.parse_fixture_text(f"{match[0]} {match[1]} vs {match[2]}")
                        if fixture_data:
                            fixtures.append(fixture_data)
            
            logger.info(f"Found {len(fixtures)} fixtures from FA page")
            return fixtures
            
        except requests.RequestException as e:
            logger.error(f"Error fetching FA page: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error parsing FA page: {str(e)}")
            return []

    def parse_fixture_row(self, cells):
        """Parse fixture data from table row."""
        try:
            if len(cells) < 3:
                return None
                
            # Extract date
            date_text = cells[0].get_text(strip=True)
            match_date = self.parse_date(date_text)
            
            # Extract opponent
            opponent = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            
            # Extract venue/location
            venue = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            
            # Extract time if available
            time_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            
            # Determine if home or away
            home_away = 'HOME' if 'home' in venue.lower() or 'vs' in opponent.lower() else 'AWAY'
            
            return {
                'date': match_date,
                'opponent': opponent,
                'venue': venue,
                'location': venue,
                'time_start': time_text,
                'home_away': home_away,
                'match_type': 'League'
            }
            
        except Exception as e:
            logger.warning(f"Error parsing fixture row: {str(e)}")
            return None

    def parse_fixture_text(self, text):
        """Parse fixture data from text."""
        try:
            # Simple regex patterns for common fixture formats
            patterns = [
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+(.+?)\s+vs\s+(.+)',
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+(.+?)\s+v\s+(.+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_str = match.group(1)
                    home_team = match.group(2).strip()
                    away_team = match.group(3).strip()
                    
                    match_date = self.parse_date(date_str)
                    
                    return {
                        'date': match_date,
                        'opponent': away_team,
                        'venue': 'Home',
                        'location': 'Home',
                        'time_start': '',
                        'home_away': 'HOME',
                        'match_type': 'League'
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing fixture text: {str(e)}")
            return None

    def parse_date(self, date_str):
        """Parse date string into datetime object."""
        try:
            # Try different date formats
            formats = [
                '%d/%m/%Y',
                '%d-%m-%Y',
                '%d/%m/%y',
                '%d-%m-%y',
                '%Y-%m-%d',
                '%d %B %Y',
                '%d %b %Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If no format matches, return current date
            logger.warning(f"Could not parse date: {date_str}")
            return datetime.now()
            
        except Exception as e:
            logger.warning(f"Error parsing date {date_str}: {str(e)}")
            return datetime.now()


class PlayCricketAPIView(APIView):
    """Import fixtures from Play Cricket API."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            team_id = request.data.get('team_id')
            if not team_id:
                return Response(
                    {"error": "Play Cricket team ID is required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found for this user. Please create a club first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Fetch fixtures from Play Cricket API
            fixtures_data = self.fetch_play_cricket_fixtures(team_id)
            
            if not fixtures_data:
                return Response(
                    {"error": "No fixtures found for the provided team ID."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Create matches
            matches_created = []
            errors = []

            for fixture in fixtures_data:
                try:
                    match = Match.objects.create(
                        club=club,
                        opponent=fixture.get('opponent', ''),
                        date=fixture.get('date'),
                        location=fixture.get('location', ''),
                        venue=fixture.get('venue', ''),
                        time_start=fixture.get('time_start', ''),
                        match_type=fixture.get('match_type', 'League'),
                        home_away=fixture.get('home_away', 'HOME')
                    )
                    matches_created.append(match.id)
                except Exception as e:
                    errors.append(f"Error creating match: {str(e)}")
                    logger.warning(f"Error creating match from Play Cricket data: {str(e)}")

            logger.info(f"Play Cricket API completed. {len(matches_created)} matches created, {len(errors)} errors")
            
            response_data = {
                "created": matches_created,
                "total_found": len(fixtures_data),
                "message": f"Successfully imported {len(matches_created)} fixtures from Play Cricket"
            }
            if errors:
                response_data["errors"] = errors

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Play Cricket API error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching Play Cricket fixtures."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def fetch_play_cricket_fixtures(self, team_id):
        """Fetch fixture data from Play Cricket API."""
        try:
            # Play Cricket API endpoint for team fixtures
            api_url = f"https://play-cricket.ecb.co.uk/api/v1/teams/{team_id}/matches"
            
            headers = {
                'User-Agent': 'MatchGen/1.0',
                'Accept': 'application/json'
            }
            
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            fixtures = []
            
            if 'data' in data:
                for match in data['data']:
                    fixture_data = self.parse_play_cricket_match(match)
                    if fixture_data:
                        fixtures.append(fixture_data)
            
            return fixtures
            
        except requests.RequestException as e:
            logger.error(f"Error fetching Play Cricket data: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error parsing Play Cricket data: {str(e)}")
            return []

    def parse_play_cricket_match(self, match_data):
        """Parse match data from Play Cricket API."""
        try:
            # Extract match details
            match_date = match_data.get('match_date')
            if match_date:
                match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
            
            home_team = match_data.get('home_team', {}).get('name', '')
            away_team = match_data.get('away_team', {}).get('name', '')
            venue = match_data.get('ground', {}).get('name', '')
            
            # Determine opponent and home/away status
            # This would need to be customized based on the club name
            opponent = away_team if home_team else home_team
            home_away = 'HOME' if home_team else 'AWAY'
            
            return {
                'date': match_date,
                'opponent': opponent,
                'venue': venue,
                'location': venue,
                'time_start': match_data.get('start_time', ''),
                'home_away': home_away,
                'match_type': match_data.get('competition', {}).get('name', 'League')
            }
            
        except Exception as e:
            logger.warning(f"Error parsing Play Cricket match: {str(e)}")
            return None


class EnhancedBulkUploadMatchesView(APIView):
    """Enhanced bulk upload matches from CSV file with better error handling."""
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
            warnings = []

            # Validate CSV headers
            required_headers = ['opponent', 'date']
            optional_headers = ['location', 'venue', 'time_start', 'match_type', 'home_away']
            
            csv_headers = reader.fieldnames or []
            missing_headers = [h for h in required_headers if h not in csv_headers]
            
            if missing_headers:
                return Response(
                    {"error": f"Missing required columns: {', '.join(missing_headers)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                try:
                    # Parse date
                    date_str = row.get("date", "")
                    if not date_str:
                        errors.append(f"Row {row_num}: Date is required")
                        continue
                    
                    try:
                        # Try different date formats
                        match_date = self.parse_csv_date(date_str)
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid date format '{date_str}'. Use DD/MM/YYYY or YYYY-MM-DD")
                        continue

                    # Create match
                    match = Match.objects.create(
                        club=club,
                        opponent=row.get("opponent", "").strip(),
                        date=match_date,
                        location=row.get("location", "").strip(),
                        venue=row.get("venue", "").strip(),
                        time_start=row.get("time_start", "").strip(),
                        match_type=row.get("match_type", "League").strip(),
                        home_away=row.get("home_away", "HOME").strip()
                    )
                    matches_created.append(match.id)
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    logger.warning(f"Error processing CSV row {row_num}: {str(e)}")

            logger.info(f"Enhanced bulk upload completed. {len(matches_created)} matches created, {len(errors)} errors")
            
            response_data = {
                "created": matches_created,
                "total_processed": len(matches_created) + len(errors),
                "message": f"Successfully imported {len(matches_created)} fixtures from CSV"
            }
            
            if errors:
                response_data["errors"] = errors
            if warnings:
                response_data["warnings"] = warnings

            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Enhanced bulk upload error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred during bulk upload."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def parse_csv_date(self, date_str):
        """Parse date string from CSV into datetime object."""
        formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y-%m-%d',
            '%d/%m/%y',
            '%d-%m-%y',
            '%d %B %Y',
            '%d %b %Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse date: {date_str}")


class FixtureImportOptionsView(APIView):
    """Get available fixture import options and their requirements."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            options = {
                "csv_upload": {
                    "name": "CSV Upload",
                    "description": "Upload a CSV file with fixture data",
                    "required_fields": ["opponent", "date"],
                    "optional_fields": ["location", "venue", "time_start", "match_type", "home_away"],
                    "sample_format": {
                        "opponent": "Team Name",
                        "date": "DD/MM/YYYY",
                        "location": "Stadium Name",
                        "venue": "Home/Away",
                        "time_start": "15:00",
                        "match_type": "League",
                        "home_away": "HOME"
                    }
                },
                "fa_fulltime": {
                    "name": "FA Fulltime Scraper",
                    "description": "Automatically import fixtures from FA Fulltime website",
                    "required_fields": ["fa_url"],
                    "example_url": "https://fulltime.thefa.com/displayTeam.html?id=562720767",
                    "note": "Paste your club's FA Fulltime team page URL",
                    "troubleshooting": "If scraping fails, try: 1) Verify the URL is accessible in your browser, 2) Check if the page requires login, 3) Use CSV upload as an alternative"
                },
                "play_cricket": {
                    "name": "Play Cricket API",
                    "description": "Import fixtures from Play Cricket API for cricket clubs",
                    "required_fields": ["team_id"],
                    "note": "Get your team ID from your Play Cricket club page URL",
                    "api_docs": "https://play-cricket.ecb.co.uk/hc/en-us/articles/360000141669-Match-Detail-API"
                },
                "ai_import": {
                    "name": "AI-Powered Import",
                    "description": "Use AI to parse fixture data from natural language text",
                    "required_fields": ["fixture_text"],
                    "example_text": "Arsenal vs Chelsea on 15/03/2024 at 15:00, Manchester United vs Liverpool on 22/03/2024 at Old Trafford",
                    "note": "Simply paste or type your fixture information in natural language",
                    "benefits": "Works with any text format, understands natural language, no specific formatting required"
                }
            }
            
            return Response(options, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting import options: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching import options."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FAFulltimeTestView(APIView):
    """Test FA Fulltime URL accessibility without importing fixtures."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            fa_url = request.data.get('fa_url')
            if not fa_url:
                return Response(
                    {"error": "FA Fulltime URL is required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate URL format
            if 'fulltime.thefa.com' not in fa_url:
                return Response(
                    {"error": "Please provide a valid FA Fulltime URL."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ensure URL has proper format
            if not fa_url.startswith('http'):
                fa_url = 'https://' + fa_url

            # Test URL accessibility
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                response = requests.get(fa_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Parse the page to check for fixture content
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for common fixture indicators
                fixture_indicators = [
                    'fixture', 'result', 'match', 'game', 'schedule', 'team', 'opponent'
                ]
                
                page_text = soup.get_text().lower()
                found_indicators = [indicator for indicator in fixture_indicators if indicator in page_text]
                
                # Check for tables that might contain fixtures
                tables = soup.find_all('table')
                table_count = len(tables)
                
                return Response({
                    "status": "success",
                    "url": fa_url,
                    "status_code": response.status_code,
                    "page_title": soup.title.string if soup.title else "No title found",
                    "fixture_indicators_found": found_indicators,
                    "table_count": table_count,
                    "page_size": len(response.content),
                    "message": "URL is accessible and contains potential fixture data"
                })
                
            except requests.exceptions.Timeout:
                return Response({
                    "status": "error",
                    "error": "Connection timeout - the FA website is not responding",
                    "suggestion": "Try again later or use CSV upload instead"
                }, status=status.HTTP_408_REQUEST_TIMEOUT)
                
            except requests.exceptions.ConnectionError:
                return Response({
                    "status": "error", 
                    "error": "Connection error - unable to reach the FA website",
                    "suggestion": "Check your internet connection or try again later"
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
            except requests.exceptions.RequestException as e:
                return Response({
                    "status": "error",
                    "error": f"Request failed: {str(e)}",
                    "suggestion": "The URL might be incorrect or the page might require authentication"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"FA test error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while testing the FA URL."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AIFixtureImportView(APIView):
    """Import fixtures using AI (ChatGPT/OpenAI) to parse natural language fixture data."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            fixture_text = request.data.get('fixture_text')
            if not fixture_text:
                return Response(
                    {"error": "Fixture text is required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found for this user. Please create a club first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Use AI to parse fixture data
            fixtures_data = self.parse_fixtures_with_ai(fixture_text, club.name)
            
            if not fixtures_data:
                return Response(
                    {
                        "error": "No fixtures could be extracted from the provided text.",
                        "suggestion": "Please provide fixture information in a clear format, such as: 'Arsenal vs Chelsea on 15/03/2024 at 15:00' or 'Manchester United vs Liverpool, 22/03/2024, Old Trafford'"
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Create matches
            matches_created = []
            errors = []

            for fixture in fixtures_data:
                try:
                    match = Match.objects.create(
                        club=club,
                        opponent=fixture.get('opponent', ''),
                        date=fixture.get('date'),
                        location=fixture.get('location', ''),
                        venue=fixture.get('venue', ''),
                        time_start=fixture.get('time_start', ''),
                        match_type=fixture.get('match_type', 'League'),
                        home_away=fixture.get('home_away', 'HOME')
                    )
                    matches_created.append(match.id)
                except Exception as e:
                    errors.append(f"Error creating match: {str(e)}")
                    logger.warning(f"Error creating match from AI data: {str(e)}")

            logger.info(f"AI fixture import completed. {len(matches_created)} matches created, {len(errors)} errors")
            
            response_data = {
                "created": matches_created,
                "total_found": len(fixtures_data),
                "message": f"Successfully imported {len(matches_created)} fixtures using AI"
            }
            if errors:
                response_data["errors"] = errors

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"AI fixture import error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while processing fixtures with AI."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def parse_fixtures_with_ai(self, fixture_text, club_name):
        """Use OpenAI to parse fixture data from natural language text."""
        try:
            import openai
            from django.conf import settings
            
            # Get OpenAI API key from settings
            openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not openai_api_key:
                logger.error("OpenAI API key not configured")
                return []
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=openai_api_key)
            
            # Create a prompt for the AI to extract fixture data
            prompt = f"""
            Extract fixture/match information from the following text and return it as a JSON array.
            The user's club is: {club_name}
            
            For each fixture, extract:
            - opponent: The team they're playing against
            - date: Match date (convert to YYYY-MM-DD format)
            - time_start: Match time (HH:MM format)
            - venue: Stadium/ground name
            - location: City or location
            - home_away: "HOME" if {club_name} is playing at home, "AWAY" if away
            - match_type: Type of match (League, Cup, Friendly, etc.)
            
            Text to parse:
            {fixture_text}
            
            Return only a JSON array of fixtures, no other text. Example format:
            [
                {{
                    "opponent": "Arsenal",
                    "date": "2024-03-15",
                    "time_start": "15:00",
                    "venue": "Emirates Stadium",
                    "location": "London",
                    "home_away": "AWAY",
                    "match_type": "League"
                }}
            ]
            """
            
            logger.info(f"Using AI to parse fixture text for club: {club_name}")
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts fixture/match information from text and returns it as structured JSON data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse the AI response
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"AI response: {ai_response}")
            
            # Try to parse as JSON
            try:
                fixtures_data = json.loads(ai_response)
                if isinstance(fixtures_data, list):
                    # Convert date strings to datetime objects
                    for fixture in fixtures_data:
                        if 'date' in fixture and fixture['date']:
                            try:
                                fixture['date'] = datetime.strptime(fixture['date'], '%Y-%m-%d')
                            except ValueError:
                                # Try other date formats
                                for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']:
                                    try:
                                        fixture['date'] = datetime.strptime(fixture['date'], fmt)
                                        break
                                    except ValueError:
                                        continue
                                else:
                                    logger.warning(f"Could not parse date: {fixture['date']}")
                                    fixture['date'] = datetime.now()
                    
                    logger.info(f"AI successfully parsed {len(fixtures_data)} fixtures")
                    return fixtures_data
                else:
                    logger.error("AI response is not a list")
                    return []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {str(e)}")
                return []
            
        except Exception as e:
            logger.error(f"AI parsing error: {str(e)}", exc_info=True)
            return []


class AIFixtureTestView(APIView):
    """Test AI fixture parsing without creating matches."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            fixture_text = request.data.get('fixture_text')
            if not fixture_text:
                return Response(
                    {"error": "Fixture text is required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found for this user. Please create a club first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Test AI parsing
            fixtures_data = self.parse_fixtures_with_ai(fixture_text, club.name)
            
            if not fixtures_data:
                return Response({
                    "status": "error",
                    "error": "No fixtures could be extracted from the provided text.",
                    "suggestion": "Try formatting your text more clearly, such as: 'Arsenal vs Chelsea on 15/03/2024 at 15:00'"
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                "status": "success",
                "fixtures_found": len(fixtures_data),
                "fixtures": fixtures_data,
                "message": f"AI successfully identified {len(fixtures_data)} fixtures"
            })
            
        except Exception as e:
            logger.error(f"AI test error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while testing AI fixture parsing."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def parse_fixtures_with_ai(self, fixture_text, club_name):
        """Use OpenAI to parse fixture data from natural language text."""
        try:
            import openai
            from django.conf import settings
            
            # Get OpenAI API key from settings
            openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not openai_api_key:
                logger.error("OpenAI API key not configured")
                return []
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=openai_api_key)
            
            # Create a prompt for the AI to extract fixture data
            prompt = f"""
            Extract fixture/match information from the following text and return it as a JSON array.
            The user's club is: {club_name}
            
            For each fixture, extract:
            - opponent: The team they're playing against
            - date: Match date (convert to YYYY-MM-DD format)
            - time_start: Match time (HH:MM format)
            - venue: Stadium/ground name
            - location: City or location
            - home_away: "HOME" if {club_name} is playing at home, "AWAY" if away
            - match_type: Type of match (League, Cup, Friendly, etc.)
            
            Text to parse:
            {fixture_text}
            
            Return only a JSON array of fixtures, no other text. Example format:
            [
                {{
                    "opponent": "Arsenal",
                    "date": "2024-03-15",
                    "time_start": "15:00",
                    "venue": "Emirates Stadium",
                    "location": "London",
                    "home_away": "AWAY",
                    "match_type": "League"
                }}
            ]
            """
            
            logger.info(f"Testing AI fixture parsing for club: {club_name}")
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts fixture/match information from text and returns it as structured JSON data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse the AI response
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"AI test response: {ai_response}")
            
            # Try to parse as JSON
            try:
                fixtures_data = json.loads(ai_response)
                if isinstance(fixtures_data, list):
                    logger.info(f"AI test successfully parsed {len(fixtures_data)} fixtures")
                    return fixtures_data
                else:
                    logger.error("AI test response is not a list")
                    return []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI test response as JSON: {str(e)}")
                return []
            
        except Exception as e:
            logger.error(f"AI test parsing error: {str(e)}", exc_info=True)
            return []
