import logging
import time
from io import BytesIO
from typing import Dict, Any

import cloudinary.uploader
import requests
from PIL import Image, ImageDraw, ImageFont
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import Club
from content.models import Match

from .models import GraphicPack, Template
from .serializers import GraphicPackSerializer

logger = logging.getLogger(__name__)


class GraphicPackListView(ListAPIView):
    """List all available graphic packs."""
    queryset = GraphicPack.objects.all()
    serializer_class = GraphicPackSerializer
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        """Override get to add debug logging and error handling."""
        try:
            response = super().get(request, *args, **kwargs)
            logger.info(f"Graphic packs response: {response.data}")
            return response
        except Exception as e:
            logger.error(f"Error in GraphicPackListView: {str(e)}", exc_info=True)
            return Response([], status=200)


class GraphicPackDetailView(RetrieveAPIView):
    """Get a single graphic pack with its templates."""
    queryset = GraphicPack.objects.all()
    serializer_class = GraphicPackSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get(self, request, *args, **kwargs):
        """Override get to add debug logging and error handling."""
        try:
            pack_id = kwargs.get('id')
            logger.info(f"Fetching graphic pack detail for ID: {pack_id}")
            
            try:
                pack = GraphicPack.objects.get(id=pack_id)
                logger.info(f"Found graphic pack: {pack.name}")
                
                templates_count = Template.objects.filter(graphic_pack=pack).count()
                logger.info(f"Found {templates_count} templates for pack {pack_id}")
                
            except GraphicPack.DoesNotExist:
                logger.error(f"Graphic pack with ID {pack_id} not found")
                return Response(
                    {"error": f"Graphic pack with ID {pack_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            try:
                response = super().get(request, *args, **kwargs)
                logger.info(f"Graphic pack detail response: {response.data}")
                return response
            except Exception as serialization_error:
                logger.error(f"Serialization error: {str(serialization_error)}")
                return Response({
                    'id': pack.id,
                    'name': pack.name,
                    'description': pack.description,
                    'preview_image_url': pack.preview_image_url,
                    'templates_count': templates_count,
                    'templates': []
                }, status=200)
                
        except Exception as e:
            logger.error(f"Error in GraphicPackDetailView: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while fetching graphic pack details."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SelectGraphicPackView(APIView):
    """Allow users to select a graphic pack for their club."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            pack_id = request.data.get('pack_id')
            if not pack_id:
                return Response(
                    {"error": "pack_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found for this user."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            try:
                graphic_pack = GraphicPack.objects.get(id=pack_id)
            except GraphicPack.DoesNotExist:
                return Response(
                    {"error": "Graphic pack not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            club.selected_pack = graphic_pack
            club.save()

            return Response({
                "message": f"Successfully selected {graphic_pack.name} for {club.name}",
                "selected_pack": {
                    "id": graphic_pack.id,
                    "name": graphic_pack.name,
                    "description": graphic_pack.description
                }
            })

        except Exception as e:
            logger.error(f"Error selecting graphic pack: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while selecting the graphic pack."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MatchdayPostGenerator(APIView):
    """Generate a Matchday social media post from a selected fixture."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate a matchday post for a specific fixture."""
        try:
            match_id = request.data.get("match_id")
            if not match_id:
                return Response(
                    {"error": "match_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found for this user."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check if club has selected a graphic pack
            if not club.selected_pack:
                return Response(
                    {"error": "No graphic pack selected for this club."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get the match
            try:
                match = Match.objects.get(id=match_id, club=club)
            except Match.DoesNotExist:
                return Response(
                    {"error": "Match not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get the matchday template
            try:
                template = Template.objects.get(
                    graphic_pack=club.selected_pack,
                    content_type="matchday"
                )
            except Template.DoesNotExist:
                return Response(
                    {"error": "Matchday template not found for this club's graphic pack."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Generate the matchday post
            result = self._generate_matchday_post(match, template, club)
            
            if result.get("error"):
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating matchday post: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while generating the matchday post."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _generate_matchday_post(self, match: Match, template: Template, club: Club) -> Dict[str, Any]:
        """Generate a matchday post with fixture details overlaid on template."""
        logger.info(f"Generating matchday post for match {match.id}, club {club.name}")
        
        # Load the template image
        try:
            response = requests.get(template.image_url, timeout=30)
            response.raise_for_status()
            base_image = Image.open(BytesIO(response.content)).convert("RGBA")
        except Exception as e:
            logger.error(f"Error loading template image: {str(e)}")
            return {"error": "Failed to load template image"}

        # Create drawing context
        draw = ImageDraw.Draw(base_image)
        
        # Get image dimensions
        image_width, image_height = base_image.size
        
        # Prepare fixture data
        fixture_data = self._prepare_fixture_data(match)
        
        # Get template configuration
        template_config = template.template_config or {}
        elements = template_config.get('elements', {})
        
        # Render text elements
        for element_key, element_config in elements.items():
            if element_config.get('type') != 'text':
                continue
                
            # Get the value for this element
            value = fixture_data.get(element_key, "")
            if not value:
                continue

            try:
                # Get element style configuration
                style = element_config.get('style', {})
                position = element_config.get('position', {})
                
                # Get font settings
                font_family = style.get('fontFamily', 'Arial')
                font_size = style.get('fontSize', 24)
                font_weight = style.get('fontWeight', 'normal')
                font_style = style.get('fontStyle', 'normal')
                
                # Get font (fallback to default if custom font fails)
                try:
                    # Try to load a custom font if available
                    font = ImageFont.truetype(f"{font_family}.ttf", font_size)
                except:
                    # Fallback to default font
                    font = ImageFont.load_default()
                
                # Get color
                color = style.get('color', '#FFFFFF')
                
                # Get position
                x_pos = position.get('x', 0)
                y_pos = position.get('y', 0)
                alignment = style.get('alignment', 'left')
                
                # Calculate text position based on alignment
                bbox = draw.textbbox((0, 0), value, font=font)
                text_width = bbox[2] - bbox[0]
                
                if alignment == 'center':
                    x = x_pos - (text_width // 2)
                elif alignment == 'right':
                    x = x_pos - text_width
                else:  # left
                    x = x_pos
                
                # Draw the text
                draw.text((x, y_pos), value, font=font, fill=color)
                logger.info(f"Rendered '{value}' at ({x}, {y_pos})")
                
            except Exception as e:
                logger.error(f"Error rendering text element {element_key}: {str(e)}")
                continue

        # Save to buffer with high resolution
        buffer = BytesIO()
        base_image.save(buffer, format="PNG", quality=95)
        buffer.seek(0)

        # Upload to Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(
                buffer,
                folder=f"matchday_posts/club_{club.id}/",
                public_id=f"matchday_{match.id}_{int(time.time())}",
                overwrite=True,
                resource_type="image",
                quality="auto:best",  # Ensure high quality
                format="png"
            )
            image_url = upload_result["secure_url"]
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {str(e)}")
            return {"error": "Failed to upload image"}

        # Update match with the generated image URL
        match.matchday_post_url = image_url
        match.save()

        return {
            "success": True,
            "image_url": image_url,
            "match_id": match.id,
            "club_name": club.name,
            "fixture_details": fixture_data,
            "message": "Matchday post generated successfully"
        }

    def _prepare_fixture_data(self, match: Match) -> Dict[str, str]:
        """Prepare fixture data for rendering on the template."""
        # Format the date
        if match.date:
            date_str = match.date.strftime("%A, %d %B %Y")
        else:
            date_str = "Date TBC"
        
        # Format the time
        if match.time_start:
            # time_start is a string like "15:00", convert to time object for formatting
            try:
                from datetime import datetime
                time_obj = datetime.strptime(match.time_start, "%H:%M")
                time_str = time_obj.strftime("%I:%M %p")
            except:
                time_str = match.time_start
        else:
            time_str = "Time TBC"
        
        # Get venue
        venue_str = match.venue or "Venue TBC"
        
        # Get opponent
        opponent_str = match.opponent or "Opponent TBC"
        
        # Since there's no is_home field, we'll use a default or determine from venue
        # For now, let's assume home games are at the club's venue
        home_away = "HOME"  # Default to HOME since we can't determine from current model
        
        return {
            "date": date_str,
            "time": time_str,
            "venue": venue_str,
            "opponent": opponent_str,
            "home_away": home_away,
            "club_name": match.club.name if match.club else "Club"
        }


class ObtainTokenView(APIView):
    """Simple view to obtain authentication token for testing."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "message": "Token endpoint - use POST with credentials to get token",
            "endpoint": "/api/token/",
            "method": "POST",
            "data": {
                "username": "your_username",
                "password": "your_password"
            }
        })