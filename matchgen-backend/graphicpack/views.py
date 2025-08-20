import csv
import io
import logging
import os
from io import BytesIO
from typing import Dict, Any, Optional

import cloudinary.uploader
import requests
from content.models import Match, Player
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont
from rest_framework import generics, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import Club
from users.serializers import LoginSerializer

from .models import (
    GraphicPack,
    Template,
    UserSelection,
)
from .serializers import GraphicPackSerializer
from .utils import get_font, parse_color, wrap_text, calculate_text_position, render_text_with_shadow

logger = logging.getLogger(__name__)


class GraphicPackListView(ListAPIView):
    """List all available graphic packs."""
    queryset = GraphicPack.objects.all()
    serializer_class = GraphicPackSerializer
    permission_classes = [AllowAny]  # Allow public access to view available packs

    def get(self, request, *args, **kwargs):
        """Override get to add debug logging and error handling."""
        try:
            response = super().get(request, *args, **kwargs)
            logger.info(f"Graphic packs response: {response.data}")
            return response
        except Exception as e:
            logger.error(f"Error in GraphicPackListView: {str(e)}", exc_info=True)
            # Fallback to simple serializer
            try:
                from .serializers import SimpleGraphicPackSerializer
                self.serializer_class = SimpleGraphicPackSerializer
                response = super().get(request, *args, **kwargs)
                logger.info(f"Fallback graphic packs response: {response.data}")
                return response
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}", exc_info=True)
                # Return empty list as last resort
                return Response([], status=200)


class GraphicPackDetailView(RetrieveAPIView):
    """Get a single graphic pack with all its templates and elements."""
    queryset = GraphicPack.objects.all()
    serializer_class = GraphicPackSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get(self, request, *args, **kwargs):
        """Override get to add debug logging and error handling."""
        try:
            pack_id = kwargs.get('id')
            logger.info(f"Fetching graphic pack detail for ID: {pack_id}")
            
            # Simple check if the pack exists
            try:
                pack = GraphicPack.objects.get(id=pack_id)
                logger.info(f"Found graphic pack: {pack.name}")
                
                # Get templates count
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
                # Return a simple response with basic pack info
                return Response({
                    'id': pack.id,
                    'name': pack.name,
                    'description': pack.description,
                    'preview_image_url': getattr(pack, 'preview_image_url', None),
                    'templates': []
                })
        except Exception as e:
            logger.error(f"Error in GraphicPackDetailView: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to load graphic pack details."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SelectGraphicPackView(APIView):
    """Select a graphic pack for the user's club."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            pack_id = request.data.get("pack_id")
            if not pack_id:
                return Response(
                    {"error": "pack_id is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            pack = get_object_or_404(GraphicPack, id=pack_id)

            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found for this user. Please create a club first."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            club.selected_pack = pack
            club.save()
            
            logger.info(f"Graphic pack '{pack.name}' selected for club '{club.name}'")
            return Response(
                {"status": "selected", "pack": pack_id, "pack_name": pack.name}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error selecting graphic pack: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while selecting the graphic pack."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GraphicGenerationView(APIView):
    """Main view for generating all types of graphics."""
    permission_classes = [IsAuthenticated]

    def post(self, request, match_id=None):
        try:
            # Extract match_id from URL if not provided in request data
            if match_id is None:
                match_id = request.data.get("match_id")
            
            # Determine content_type from URL path if not provided in request data
            content_type = request.data.get("content_type")
            if content_type is None:
                # Extract content_type from URL path
                path = request.path
                if "generate-upcoming" in path:
                    content_type = "upcomingFixture"
                elif "generate-startingxi" in path:
                    content_type = "startingXI"
                elif "generate-goal" in path:
                    content_type = "goal"
                elif "generate-substitution" in path:
                    content_type = "sub"
                elif "generate-halftime" in path:
                    content_type = "halftime"
                elif "generate-fulltime" in path:
                    content_type = "fulltime"
                elif "generate-matchday" in path:
                    content_type = "matchday"
            
            player_id = request.data.get("player_id")
            regenerate = request.data.get("regenerate", False)  # New parameter
            
            if not content_type:
                return Response(
                    {"error": "content_type is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

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

            if not club.selected_pack:
                return Response(
                    {"error": "No graphic pack selected for this club."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Generate based on content type
            if content_type == "matchday":
                match = get_object_or_404(Match, id=match_id, club=club)
                result = self._generate_matchday(match, club, regenerate=regenerate)
            
            elif content_type == "startingXI":
                match = get_object_or_404(Match, id=match_id, club=club)
                result = self._generate_starting_xi(match, club, regenerate=regenerate)
            
            elif content_type == "upcomingFixture":
                match = get_object_or_404(Match, id=match_id, club=club)
                result = self._generate_upcoming_fixture(match, club, regenerate=regenerate)
            
            elif content_type == "goal":
                match = get_object_or_404(Match, id=match_id, club=club)
                scorer_name = request.data.get("scorer_name", "Player")
                result = self._generate_goal(match, club, scorer_name, regenerate=regenerate)
            
            elif content_type == "sub":
                match = get_object_or_404(Match, id=match_id, club=club)
                player_in = request.data.get("player_in", "Player In")
                player_out = request.data.get("player_out", "Player Out")
                result = self._generate_sub(match, club, player_in, player_out, regenerate=regenerate)
            
            elif content_type == "halftime":
                match = get_object_or_404(Match, id=match_id, club=club)
                score = request.data.get("score", "0-0")
                result = self._generate_halftime(match, club, score, regenerate=regenerate)
            
            elif content_type == "fulltime":
                match = get_object_or_404(Match, id=match_id, club=club)
                score = request.data.get("score", "0-0")
                result = self._generate_fulltime(match, club, score, regenerate=regenerate)
            
            else:
                return Response(
                    {"error": f"Unsupported content_type: {content_type}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if result.get("error"):
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating graphic: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while generating the graphic."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_template(self, club: Club, content_type: str) -> Optional[Template]:
        """Get template for the specified content type."""
        try:
            return club.selected_pack.templates.get(content_type=content_type)
        except Template.DoesNotExist:
            logger.error(f"Template {content_type} not found in pack {club.selected_pack.name}")
            return None

    def _load_base_image(self, template: Template) -> Optional[Image.Image]:
        """Load base image from template URL."""
        try:
            response = requests.get(template.image_url, timeout=30)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGBA")
        except requests.RequestException as e:
            logger.error(f"Error loading template image: {str(e)}")
            return None

    def _render_text_elements(self, draw: ImageDraw.Draw, template: Template, content: Dict[str, Any]):
        """Render all text elements on the image using JSON-based configuration."""
        logger.info(f"Rendering text elements for template {template.id}")
        logger.info(f"Available content keys: {list(content.keys())}")
        
        # Get image dimensions for percentage calculations
        image_width, image_height = draw.im.size
        
        # Get template configuration
        template_config = template.template_config or {}
        elements = template_config.get('elements', {})
        logger.info(f"Found {len(elements)} elements in template configuration")
        
        for element_key, element_config in elements.items():
            if element_config.get('type') != 'text':
                continue
                
            logger.info(f"Processing text element: {element_key}")
            value = content.get(element_key, "")
            logger.info(f"Value for {element_key}: '{value}'")
            
            if not value:
                logger.warning(f"No value found for content key: {element_key}")
                continue

            try:
                # Get element style configuration
                style = element_config.get('style', {})
                position = element_config.get('position', {})
                
                # Get font with enhanced styling
                font_family = style.get('fontFamily', 'Arial')
                font_size = style.get('fontSize', 24)
                font_weight = style.get('fontWeight', 'normal')
                font_style = style.get('fontStyle', 'normal')
                
                font = get_font(font_family, font_size, font_weight, font_style)
                
                # Parse and validate color
                color = parse_color(style.get('color', '#FFFFFF'))
                
                # Handle text wrapping if max_width is specified
                max_width = style.get('maxWidth')
                if max_width:
                    lines = wrap_text(value, font, max_width, draw)
                else:
                    lines = [value]
                
                # Calculate line height
                bbox = draw.textbbox((0, 0), "Ay", font=font)  # Use "Ay" to get proper line height
                line_height = (bbox[3] - bbox[1]) * style.get('lineHeight', 1.2)
                
                # Get position
                x_pos = position.get('x', 0)
                y_pos = position.get('y', 0)
                alignment = style.get('alignment', 'left')
                
                # Render each line
                for i, line in enumerate(lines):
                    # Calculate position for this line
                    x, y = calculate_text_position(
                        x_pos, 
                        y_pos + (i * line_height), 
                        line, 
                        font, 
                        alignment, 
                        draw,
                        False,  # Not using percentage for now
                        image_width,
                        image_height
                    )
                    
                    # Render text with shadow if enabled
                    if style.get('textShadow'):
                        shadow_color = style.get('shadowColor', '#000000')
                        shadow_offset_x = style.get('shadowOffsetX', 2)
                        shadow_offset_y = style.get('shadowOffsetY', 2)
                        render_text_with_shadow(
                            draw,
                            line,
                            (x, y),
                            font,
                            color,
                            shadow_color,
                            (shadow_offset_x, shadow_offset_y)
                        )
                    else:
                        draw.text((x, y), line, font=font, fill=color)
                    
                    logger.info(f"Rendered line '{line}' at ({x}, {y}) with color {color}")
                    
            except Exception as e:
                logger.error(f"Error rendering text element {element_key}: {str(e)}", exc_info=True)
                continue

    def _render_image_elements(self, base_image: Image.Image, template: Template, content: Dict[str, Any]):
        """Render all image elements on the base image."""
        logger.info(f"Rendering image elements for template {template.id}")
        
        elements = template.elements.filter(type="image")
        logger.info(f"Found {elements.count()} image elements")
        
        for element in elements:
            logger.info(f"Processing image element: {element.content_key} at ({element.x}, {element.y})")
            for image in element.image_elements.all():
                logger.info(f"Processing image element: {image.content_key}")
                image_url = content.get(image.content_key)
                logger.info(f"Image URL for {image.content_key}: {image_url}")
                
                if not image_url:
                    logger.warning(f"No image URL found for content key: {image.content_key}")
                    continue
                
                try:
                    img_response = requests.get(image_url, timeout=30)
                    img_response.raise_for_status()
                    img = Image.open(BytesIO(img_response.content)).convert("RGBA")

                    if image.maintain_aspect_ratio:
                        img.thumbnail((element.width, element.height))
                    else:
                        img = img.resize((int(element.width), int(element.height)))

                    logger.info(f"Pasting image at ({int(element.x)}, {int(element.y)})")
                    base_image.paste(img, (int(element.x), int(element.y)), img)
                except Exception as e:
                    logger.error(f"Error loading image {image.content_key}: {str(e)}", exc_info=True)
                    continue

    def _upload_to_cloudinary(self, image_buffer: BytesIO, club: Club, content_type: str, identifier: str) -> Optional[str]:
        """Upload generated image to Cloudinary."""
        try:
            upload_result = cloudinary.uploader.upload(
                image_buffer,
                folder=f"{content_type}_posts/club_{club.id}/",
                public_id=f"{content_type}_{identifier}",
                overwrite=True,
                resource_type="image",
            )
            return upload_result["secure_url"]
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {str(e)}")
            return None

    def _generate_graphic(self, template: Template, content: Dict[str, Any], club: Club, content_type: str, identifier: str) -> Dict[str, Any]:
        """Generic graphic generation method."""
        # Load base image
        base_image = self._load_base_image(template)
        if not base_image:
            return {"error": "Failed to load template image"}

        # Create drawing context
        draw = ImageDraw.Draw(base_image)

        # Render elements
        self._render_text_elements(draw, template, content)
        self._render_image_elements(base_image, template, content)

        # Save to buffer
        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        buffer.seek(0)

        # Upload to Cloudinary
        url = self._upload_to_cloudinary(buffer, club, content_type, identifier)
        if not url:
            return {"error": "Failed to upload image"}

        return {"url": url}

    def _generate_matchday(self, match: Match, club: Club, regenerate: bool = False) -> Dict[str, Any]:
        """Generate matchday graphic."""
        logger.info(f"Generating matchday graphic for match {match.id}, club {club.name}, regenerate={regenerate}")
        
        # Check if graphic already exists
        if match.matchday_post_url and not regenerate:
            logger.info(f"Matchday graphic already exists for match {match.id}")
            return {
                "url": match.matchday_post_url,
                "already_exists": True,
                "message": "Graphic already generated. Use regenerate=true to create a new version."
            }
        
        template = self._get_template(club, "matchday")
        if not template:
            logger.error(f"Matchday template not found for club {club.name}")
            return {"error": "Matchday template not found"}

        logger.info(f"Found template: {template.id} - {template.content_type}")

        content = {
            "club_name": club.name,
            "opponent": match.opponent,
            "Versus": "Versus",
            "date": match.date.strftime("%d.%m.%Y"),
            "start": "Kick Off",
            "time": match.time_start or match.date.strftime("%I:%M %p"),
            "venue": match.venue or "Venue",
            "club_logo": match.club_logo,
            "opponent_logo": match.opponent_logo,
        }

        logger.info(f"Generated content for matchday: {content}")

        result = self._generate_graphic(template, content, club, "matchday", f"match_{match.id}")
        
        # Update match with generated URL
        if result.get("url"):
            match.matchday_post_url = result["url"]
            match.save()
            logger.info(f"Updated match {match.id} with generated URL: {result['url']}")
            
            # Add regeneration info to response
            if regenerate:
                result["regenerated"] = True
                result["message"] = "Graphic regenerated successfully"
            else:
                result["generated"] = True
                result["message"] = "Graphic generated successfully"
        
        return result

    def _generate_starting_xi(self, match: Match, club: Club, regenerate: bool = False) -> Dict[str, Any]:
        """Generate starting XI graphic."""
        template = self._get_template(club, "lineup")
        if not template:
            return {"error": "Lineup template not found"}

        # Get players for this match (you might want to add a field to track starting XI)
        players = Player.objects.filter(club=club)[:11]  # Get first 11 players
        
        content = {
            "club_name": club.name,
            "opponent": match.opponent,
            "date": match.date.strftime("%d.%m.%Y"),
            "club_logo": match.club_logo,
            "opponent_logo": match.opponent_logo,
            "formation": "4-4-2",  # You might want to make this dynamic
        }

        # Add player names (you'll need to adjust based on your template structure)
        for i, player in enumerate(players[:11]):
            content[f"player_{i+1}"] = player.name
            content[f"position_{i+1}"] = player.position

        return self._generate_graphic(template, content, club, "startingXI", f"match_{match.id}")

    def _generate_upcoming_fixture(self, match: Match, club: Club, regenerate: bool = False) -> Dict[str, Any]:
        """Generate upcoming fixture graphic."""
        template = self._get_template(club, "fixture")
        if not template:
            return {"error": "Fixture template not found"}

        content = {
            "club_name": club.name,
            "opponent": match.opponent,
            "date": match.date.strftime("%d.%m.%Y"),
            "time": match.time_start or match.date.strftime("%I:%M %p"),
            "venue": match.venue or "Venue",
            "club_logo": match.club_logo,
            "opponent_logo": match.opponent_logo,
            "fixture_type": match.match_type,
        }

        return self._generate_graphic(template, content, club, "upcomingFixture", f"match_{match.id}")

    def _generate_goal(self, match: Match, club: Club, scorer_name: str, regenerate: bool = False) -> Dict[str, Any]:
        """Generate goal celebration graphic."""
        template = self._get_template(club, "alert")
        if not template:
            return {"error": "Alert template not found"}

        content = {
            "club_name": club.name,
            "opponent": match.opponent,
            "scorer": scorer_name,
            "goal_text": "GOAL!",
            "club_logo": match.club_logo,
            "opponent_logo": match.opponent_logo,
        }

        return self._generate_graphic(template, content, club, "goal", f"match_{match.id}_{scorer_name}")

    def _generate_sub(self, match: Match, club: Club, player_in: str, player_out: str, regenerate: bool = False) -> Dict[str, Any]:
        """Generate substitution graphic."""
        template = self._get_template(club, "alert")
        if not template:
            return {"error": "Alert template not found"}

        content = {
            "club_name": club.name,
            "opponent": match.opponent,
            "player_in": player_in,
            "player_out": player_out,
            "sub_text": "SUBSTITUTION",
            "club_logo": match.club_logo,
            "opponent_logo": match.opponent_logo,
        }

        return self._generate_graphic(template, content, club, "sub", f"match_{match.id}_{player_in}")

    def _generate_halftime(self, match: Match, club: Club, score: str, regenerate: bool = False) -> Dict[str, Any]:
        """Generate halftime score graphic."""
        template = self._get_template(club, "result")
        if not template:
            return {"error": "Result template not found"}

        content = {
            "club_name": club.name,
            "opponent": match.opponent,
            "score": score,
            "period": "HALF TIME",
            "club_logo": match.club_logo,
            "opponent_logo": match.opponent_logo,
        }

        return self._generate_graphic(template, content, club, "halftime", f"match_{match.id}")

    def _generate_fulltime(self, match: Match, club: Club, score: str, regenerate: bool = False) -> Dict[str, Any]:
        """Generate fulltime result graphic."""
        template = self._get_template(club, "result")
        if not template:
            return {"error": "Result template not found"}

        content = {
            "club_name": club.name,
            "opponent": match.opponent,
            "score": score,
            "period": "FULL TIME",
            "club_logo": match.club_logo,
            "opponent_logo": match.opponent_logo,
        }

        result = self._generate_graphic(template, content, club, "fulltime", f"match_{match.id}")
        
        # Update match with result URL
        if result.get("url"):
            match.matchday_post_url = result["url"]
            match.save()
        
        return result


class RegenerateGraphicView(APIView):
    """Regenerate a graphic that already exists."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            content_type = request.data.get("content_type")
            match_id = request.data.get("match_id")
            player_id = request.data.get("player_id")
            
            if not content_type:
                return Response(
                    {"error": "content_type is required"}, 
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

            if not club.selected_pack:
                return Response(
                    {"error": "No graphic pack selected for this club."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Force regeneration by setting regenerate=True
            regenerate = True

            # Generate based on content type (same logic as GraphicGenerationView)
            if content_type == "matchday":
                if not match_id:
                    return Response(
                        {"error": "match_id is required for matchday graphics"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                match = get_object_or_404(Match, id=match_id, club=club)
                result = self._generate_matchday(match, club, regenerate=regenerate)
            
            elif content_type == "startingXI":
                if not match_id:
                    return Response(
                        {"error": "match_id is required for startingXI graphics"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                match = get_object_or_404(Match, id=match_id, club=club)
                result = self._generate_starting_xi(match, club, regenerate=regenerate)
            
            elif content_type == "upcomingFixture":
                if not match_id:
                    return Response(
                        {"error": "match_id is required for upcomingFixture graphics"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                match = get_object_or_404(Match, id=match_id, club=club)
                result = self._generate_upcoming_fixture(match, club, regenerate=regenerate)
            
            elif content_type == "goal":
                if not match_id:
                    return Response(
                        {"error": "match_id is required for goal graphics"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                match = get_object_or_404(Match, id=match_id, club=club)
                scorer_name = request.data.get("scorer_name", "Player")
                result = self._generate_goal(match, club, scorer_name, regenerate=regenerate)
            
            elif content_type == "sub":
                if not match_id:
                    return Response(
                        {"error": "match_id is required for sub graphics"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                match = get_object_or_404(Match, id=match_id, club=club)
                player_in = request.data.get("player_in", "Player In")
                player_out = request.data.get("player_out", "Player Out")
                result = self._generate_sub(match, club, player_in, player_out, regenerate=regenerate)
            
            elif content_type == "halftime":
                if not match_id:
                    return Response(
                        {"error": "match_id is required for halftime graphics"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                match = get_object_or_404(Match, id=match_id, club=club)
                score = request.data.get("score", "0-0")
                result = self._generate_halftime(match, club, score, regenerate=regenerate)
            
            elif content_type == "fulltime":
                if not match_id:
                    return Response(
                        {"error": "match_id is required for fulltime graphics"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                match = get_object_or_404(Match, id=match_id, club=club)
                score = request.data.get("score", "0-0")
                result = self._generate_fulltime(match, club, score, regenerate=regenerate)
            
            else:
                return Response(
                    {"error": f"Unsupported content_type: {content_type}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if result.get("error"):
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error regenerating graphic: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while regenerating the graphic."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _generate_matchday(self, match: Match, club: Club, regenerate: bool = False) -> Dict[str, Any]:
        """Generate matchday graphic."""
        logger.info(f"Regenerating matchday graphic for match {match.id}, club {club.name}")
        
        template = self._get_template(club, "matchday")
        if not template:
            logger.error(f"Matchday template not found for club {club.name}")
            return {"error": "Matchday template not found"}

        logger.info(f"Found template: {template.id} - {template.content_type}")

        content = {
            "club_name": club.name,
            "opponent": match.opponent,
            "Versus": "Versus",
            "date": match.date.strftime("%d.%m.%Y"),
            "start": "Kick Off",
            "time": match.time_start or match.date.strftime("%I:%M %p"),
            "venue": match.venue or "Venue",
            "club_logo": match.club_logo,
            "opponent_logo": match.opponent_logo,
        }

        logger.info(f"Generated content for matchday: {content}")

        result = self._generate_graphic(template, content, club, "matchday", f"match_{match.id}")
        
        # Update match with generated URL
        if result.get("url"):
            match.matchday_post_url = result["url"]
            match.save()
            logger.info(f"Updated match {match.id} with regenerated URL: {result['url']}")
            
            result["regenerated"] = True
            result["message"] = "Graphic regenerated successfully"
        
        return result

    def _get_template(self, club: Club, content_type: str) -> Optional[Template]:
        """Get template for the specified content type."""
        try:
            return club.selected_pack.templates.get(content_type=content_type)
        except Template.DoesNotExist:
            logger.error(f"Template {content_type} not found in pack {club.selected_pack.name}")
            return None

    def _generate_graphic(self, template: Template, content: Dict[str, Any], club: Club, content_type: str, identifier: str) -> Dict[str, Any]:
        """Generic graphic generation method."""
        # Load base image
        try:
            response = requests.get(template.image_url, timeout=30)
            response.raise_for_status()
            base_image = Image.open(BytesIO(response.content)).convert("RGBA")
        except requests.RequestException as e:
            logger.error(f"Error loading template image: {str(e)}")
            return {"error": "Failed to load template image"}

        # Create drawing context
        draw = ImageDraw.Draw(base_image)

        # Render elements
        self._render_text_elements(draw, template, content)
        self._render_image_elements(base_image, template, content)

        # Save to buffer
        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        buffer.seek(0)

        # Upload to Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(
                buffer,
                folder=f"{content_type}_posts/club_{club.id}/",
                public_id=f"{content_type}_{identifier}",
                overwrite=True,
                resource_type="image",
            )
            return {"url": upload_result["secure_url"]}
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {str(e)}")
            return {"error": "Failed to upload image"}

    def _render_text_elements(self, draw: ImageDraw.Draw, template: Template, content: Dict[str, Any]):
        """Render all text elements on the image."""
        logger.info(f"Rendering text elements for template {template.id}")
        logger.info(f"Available content keys: {list(content.keys())}")
        
        elements = template.elements.filter(type="text")
        logger.info(f"Found {elements.count()} text elements")
        
        for element in elements:
            logger.info(f"Processing text element: {element.content_key} at ({element.x}, {element.y})")
            for string in element.string_elements.all():
                logger.info(f"Processing string element: {string.content_key}")
                value = content.get(string.content_key, "")
                logger.info(f"Value for {string.content_key}: '{value}'")
                
                if not value:
                    logger.warning(f"No value found for content key: {string.content_key}")
                    continue

                try:
                    font = get_font(string.font_family, string.font_size)
                    
                    # Handle text alignment
                    if string.alignment == "center":
                        bbox = draw.textbbox((0, 0), value, font=font)
                        text_width = bbox[2] - bbox[0]
                        x = element.x - (text_width / 2)
                    elif string.alignment == "right":
                        bbox = draw.textbbox((0, 0), value, font=font)
                        text_width = bbox[2] - bbox[0]
                        x = element.x - text_width
                    else:  # left alignment
                        x = element.x

                    logger.info(f"Drawing text '{value}' at ({x}, {element.y}) with color {string.color}")
                    draw.text((x, element.y), value, font=font, fill=string.color)
                except Exception as e:
                    logger.error(f"Error rendering text element {string.content_key}: {str(e)}", exc_info=True)
                    continue

    def _render_image_elements(self, base_image: Image.Image, template: Template, content: Dict[str, Any]):
        """Render all image elements on the base image."""
        logger.info(f"Rendering image elements for template {template.id}")
        
        elements = template.elements.filter(type="image")
        logger.info(f"Found {elements.count()} image elements")
        
        for element in elements:
            logger.info(f"Processing image element: {element.content_key} at ({element.x}, {element.y})")
            for image in element.image_elements.all():
                logger.info(f"Processing image element: {image.content_key}")
                image_url = content.get(image.content_key)
                logger.info(f"Image URL for {image.content_key}: {image_url}")
                
                if not image_url:
                    logger.warning(f"No image URL found for content key: {image.content_key}")
                    continue
                
                try:
                    img_response = requests.get(image_url, timeout=30)
                    img_response.raise_for_status()
                    img = Image.open(BytesIO(img_response.content)).convert("RGBA")

                    if image.maintain_aspect_ratio:
                        img.thumbnail((element.width, element.height))
                    else:
                        img = img.resize((int(element.width), int(element.height)))

                    logger.info(f"Pasting image at ({int(element.x)}, {int(element.y)})")
                    base_image.paste(img, (int(element.x), int(element.y)), img)
                except Exception as e:
                    logger.error(f"Error loading image {image.content_key}: {str(e)}", exc_info=True)
                    continue


class TemplateEditorView(APIView):
    """Handle template editing operations with JSON-based configuration."""
    permission_classes = [IsAuthenticated]

    def get(self, request, template_id):
        """Get template configuration for editing."""
        try:
            template = get_object_or_404(Template, id=template_id)
            
            # Check if user has access to this template
            try:
                club = Club.objects.get(user=request.user)
                if template.graphic_pack != club.selected_pack:
                    return Response(
                        {"error": "You don't have access to this template."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found for this user."},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response({
                'template_id': template.id,
                'template_name': f"{template.graphic_pack.name} - {template.content_type}",
                'template_config': template.template_config or {},
                'image_url': template.image_url
            })
            
        except Exception as e:
            logger.error(f"Error getting template configuration: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while getting template configuration."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, template_id):
        """Update template configuration."""
        try:
            template = get_object_or_404(Template, id=template_id)
            
            # Check if user has access to this template
            try:
                club = Club.objects.get(user=request.user)
                if template.graphic_pack != club.selected_pack:
                    return Response(
                        {"error": "You don't have access to this template."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Club.DoesNotExist:
                return Response(
                    {"error": "Club not found for this user."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update the template configuration
            template_config = request.data.get('template_config', {})
            template.template_config = template_config
            template.save()

            return Response({
                'message': 'Template configuration updated successfully',
                'template_id': template.id,
                'template_config': template.template_config
            })

        except Exception as e:
            logger.error(f"Error updating template configuration: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while updating template configuration."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Legacy function for backward compatibility
def generate_matchday(request, match_id):
    """Legacy function - now redirects to the new API."""
    try:
        match = get_object_or_404(Match, id=match_id)
        club = match.club
        
        if not club.selected_pack:
            return JsonResponse({"error": "Club has no selected graphic pack."}, status=400)

        # Check if regenerate parameter is provided
        regenerate = request.GET.get('regenerate', 'false').lower() == 'true'
        
        # Use the new generation system
        view = GraphicGenerationView()
        view.request = request
        result = view._generate_matchday(match, club, regenerate=regenerate)
        
        if result.get("error"):
            return JsonResponse({"error": result["error"]}, status=500)
        
        # Return appropriate response based on result
        response_data = {"url": result["url"]}
        
        if result.get("already_exists"):
            response_data["already_exists"] = True
            response_data["message"] = result["message"]
        elif result.get("regenerated"):
            response_data["regenerated"] = True
            response_data["message"] = result["message"]
        elif result.get("generated"):
            response_data["generated"] = True
            response_data["message"] = result["message"]
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in legacy generate_matchday: {str(e)}", exc_info=True)
        return JsonResponse({"error": "An error occurred while generating the graphic."}, status=500)


class ObtainTokenView(APIView):
    """Obtain JWT token for authentication."""
    authentication_classes = []  # allow unauthenticated
    permission_classes = []

    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            logger.info(f"Token obtained successfully for user")
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error obtaining token: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred during authentication."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DebugGraphicPackView(APIView):
    """Debug view to check graphic pack data."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            packs = GraphicPack.objects.all()
            pack_data = []
            
            for pack in packs:
                try:
                    pack_info = {
                        'id': pack.id,
                        'name': pack.name,
                        'description': pack.description,
                        'templates_count': 0,
                        'templates': []
                    }
                    
                    # Try to get templates count safely
                    try:
                        pack_info['templates_count'] = pack.templates.count()
                    except Exception as e:
                        logger.warning(f"Could not count templates for pack {pack.id}: {str(e)}")
                    
                    # Try to get templates safely
                    try:
                        for template in pack.templates.all():
                            try:
                                template_info = {
                                    'id': template.id,
                                    'content_type': template.content_type,
                                    'elements_count': 0,
                                    'elements': []
                                }
                                
                                # Try to count elements safely
                                try:
                                    template_info['elements_count'] = template.elements.count()
                                except Exception as e:
                                    logger.warning(f"Could not count elements for template {template.id}: {str(e)}")
                                
                                # Try to get elements safely
                                try:
                                    for element in template.elements.all():
                                        try:
                                            element_info = {
                                                'id': element.id,
                                                'type': element.type,
                                                'content_key': element.content_key,
                                                'string_elements_count': 0,
                                                'image_elements_count': 0
                                            }
                                            
                                            # Try to count string and image elements safely
                                            try:
                                                element_info['string_elements_count'] = element.string_elements.count()
                                            except Exception as e:
                                                logger.warning(f"Could not count string elements for element {element.id}: {str(e)}")
                                            
                                            try:
                                                element_info['image_elements_count'] = element.image_elements.count()
                                            except Exception as e:
                                                logger.warning(f"Could not count image elements for element {element.id}: {str(e)}")
                                            
                                            template_info['elements'].append(element_info)
                                        except Exception as e:
                                            logger.warning(f"Error processing element: {str(e)}")
                                            continue
                                except Exception as e:
                                    logger.warning(f"Error getting elements for template {template.id}: {str(e)}")
                                
                                pack_info['templates'].append(template_info)
                            except Exception as e:
                                logger.warning(f"Error processing template: {str(e)}")
                                continue
                    except Exception as e:
                        logger.warning(f"Error getting templates for pack {pack.id}: {str(e)}")
                    
                    pack_data.append(pack_info)
                except Exception as e:
                    logger.warning(f"Error processing pack {pack.id}: {str(e)}")
                    continue
            
            return Response({
                'total_packs': len(pack_data),
                'packs': pack_data
            })
            
        except Exception as e:
            logger.error(f"Error in debug view: {str(e)}", exc_info=True)
            return Response({
                'error': str(e)
            }, status=500)


class TestAPIView(APIView):
    """Simple test endpoint to check if API is working."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'ok',
            'message': 'API is working',
            'timestamp': timezone.now().isoformat()
        })


class CreateTestDataView(APIView):
    """Create test templates for development with JSON-based configuration."""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Create a test graphic pack
            pack, created = GraphicPack.objects.get_or_create(
                name="Test Pack",
                defaults={
                    'description': 'Test graphic pack with templates',
                    'preview_image_url': 'https://via.placeholder.com/400x300',
                }
            )
            
            if created:
                logger.info(f'Created graphic pack: {pack.name}')
            else:
                logger.info(f'Using existing graphic pack: {pack.name}')

            # Create template configuration
            template_config = {
                "elements": {
                    "club_name": {
                        "type": "text",
                        "position": {"x": 400, "y": 100},
                        "style": {
                            "fontSize": 24,
                            "fontFamily": "Arial",
                            "color": "#FFFFFF",
                            "alignment": "center"
                        }
                    },
                    "opponent": {
                        "type": "text",
                        "position": {"x": 400, "y": 150},
                        "style": {
                            "fontSize": 24,
                            "fontFamily": "Arial",
                            "color": "#FFFFFF",
                            "alignment": "center"
                        }
                    },
                    "date": {
                        "type": "text",
                        "position": {"x": 400, "y": 200},
                        "style": {
                            "fontSize": 20,
                            "fontFamily": "Arial",
                            "color": "#FFFFFF",
                            "alignment": "center"
                        }
                    },
                    "venue": {
                        "type": "text",
                        "position": {"x": 400, "y": 250},
                        "style": {
                            "fontSize": 20,
                            "fontFamily": "Arial",
                            "color": "#FFFFFF",
                            "alignment": "center"
                        }
                    }
                }
            }

            # Create a matchday template with JSON configuration
            template, created = Template.objects.get_or_create(
                graphic_pack=pack,
                content_type='matchday',
                defaults={
                    'image_url': 'https://via.placeholder.com/800x600',
                    'sport': 'football',
                    'template_config': template_config
                }
            )
            
            if created:
                logger.info(f'Created matchday template: {template.id}')
            else:
                # Update existing template with new configuration
                template.template_config = template_config
                template.save()
                logger.info(f'Updated existing matchday template: {template.id}')

            return Response({
                'message': 'Test data created successfully',
                'pack_id': pack.id,
                'template_id': template.id,
                'elements_created': len(template_config['elements']),
                'template_config': template_config
            })
            
        except Exception as e:
            logger.error(f"Error creating test data: {str(e)}", exc_info=True)
            return Response({
                'error': str(e)
            }, status=500)


class DebugTemplatesView(APIView):
    """Debug endpoint to check templates for a specific graphic pack."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            pack_id = request.query_params.get('pack_id', 7)  # Default to pack 7
            
            # Get the graphic pack
            try:
                pack = GraphicPack.objects.get(id=pack_id)
            except GraphicPack.DoesNotExist:
                return Response({
                    'error': f'Graphic pack with ID {pack_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get all templates for this pack
            templates = Template.objects.filter(graphic_pack=pack)
            
            template_data = []
            for template in templates:
                template_config = template.template_config or {}
                elements = template_config.get('elements', {})
                template_data.append({
                    'id': template.id,
                    'content_type': template.content_type,
                    'image_url': template.image_url,
                    'sport': template.sport,
                    'elements_count': len(elements),
                    'template_config': template_config
                })
            
            # Also check all templates in the database
            all_templates = Template.objects.all()
            all_template_data = []
            for template in all_templates:
                template_config = template.template_config or {}
                elements = template_config.get('elements', {})
                all_template_data.append({
                    'id': template.id,
                    'graphic_pack_id': template.graphic_pack.id,
                    'graphic_pack_name': template.graphic_pack.name,
                    'content_type': template.content_type,
                    'elements_count': len(elements)
                })
            
            return Response({
                'pack_id': pack_id,
                'pack_name': pack.name,
                'templates_count': templates.count(),
                'templates': template_data,
                'all_templates_count': all_templates.count(),
                'all_templates': all_template_data,
                'database_info': {
                    'total_graphic_packs': GraphicPack.objects.count(),
                    'total_templates': Template.objects.count()
                }
            })
            
        except Exception as e:
            logger.error(f"Error in DebugTemplatesView: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to debug templates: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateMissingTemplatesView(APIView):
    """Create missing templates for all graphic packs with JSON-based configuration."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            from .models import GraphicPack, Template
            from django.db import transaction
            
            # Get all graphic packs
            graphic_packs = GraphicPack.objects.all()
            
            # Define the content types that the backend expects
            content_types = [
                "matchday",
                "upcomingFixture", 
                "startingXI",
                "goal",
                "sub",
                "halftime",
                "fulltime"
            ]
            
            created_templates = []
            
            for pack in graphic_packs:
                # Check existing templates
                existing_templates = Template.objects.filter(graphic_pack=pack)
                existing_content_types = [t.content_type for t in existing_templates]
                
                # Create missing templates
                for content_type in content_types:
                    if content_type not in existing_content_types:
                        try:
                            with transaction.atomic():
                                # Create template configuration based on content type
                                if content_type == "matchday":
                                    template_config = {
                                        "elements": {
                                            "date": {
                                                "type": "text",
                                                "position": {"x": 200, "y": 150},
                                                "style": {
                                                    "fontSize": 24,
                                                    "fontFamily": "Arial",
                                                    "color": "#FFFFFF",
                                                    "alignment": "center"
                                                }
                                            },
                                            "time": {
                                                "type": "text",
                                                "position": {"x": 400, "y": 150},
                                                "style": {
                                                    "fontSize": 24,
                                                    "fontFamily": "Arial",
                                                    "color": "#FFFFFF",
                                                    "alignment": "center"
                                                }
                                            },
                                            "venue": {
                                                "type": "text",
                                                "position": {"x": 300, "y": 250},
                                                "style": {
                                                    "fontSize": 20,
                                                    "fontFamily": "Arial",
                                                    "color": "#FFFFFF",
                                                    "alignment": "center"
                                                }
                                            }
                                        }
                                    }
                                elif content_type == "upcomingFixture":
                                    template_config = {
                                        "elements": {
                                            "opponent": {
                                                "type": "text",
                                                "position": {"x": 300, "y": 200},
                                                "style": {
                                                    "fontSize": 24,
                                                    "fontFamily": "Arial",
                                                    "color": "#FFFFFF",
                                                    "alignment": "center"
                                                }
                                            },
                                            "date": {
                                                "type": "text",
                                                "position": {"x": 300, "y": 250},
                                                "style": {
                                                    "fontSize": 20,
                                                    "fontFamily": "Arial",
                                                    "color": "#FFFFFF",
                                                    "alignment": "center"
                                                }
                                            }
                                        }
                                    }
                                else:
                                    template_config = {
                                        "elements": {
                                            "title": {
                                                "type": "text",
                                                "position": {"x": 300, "y": 200},
                                                "style": {
                                                    "fontSize": 24,
                                                    "fontFamily": "Arial",
                                                    "color": "#FFFFFF",
                                                    "alignment": "center"
                                                }
                                            }
                                        }
                                    }
                                
                                # Create the template with JSON configuration
                                template = Template.objects.create(
                                    graphic_pack=pack,
                                    content_type=content_type,
                                    image_url=f"https://via.placeholder.com/800x600/1976d2/ffffff?text={content_type}+Template",
                                    sport="football",
                                    template_config=template_config
                                )
                                
                                created_templates.append({
                                    'pack_name': pack.name,
                                    'pack_id': pack.id,
                                    'template_id': template.id,
                                    'content_type': content_type
                                })
                                
                        except Exception as e:
                            logger.error(f"Error creating template for {content_type} in pack {pack.name}: {str(e)}")
            
            return Response({
                'message': f'Successfully created {len(created_templates)} missing templates',
                'created_templates': created_templates
            })
            
        except Exception as e:
            logger.error(f"Error in CreateMissingTemplatesView: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to create missing templates: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TestGraphicPackDetailView(APIView):
    """Test endpoint to debug graphic pack detail issues."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            pack_id = request.query_params.get('pack_id', 8)
            logger.info(f"Testing graphic pack detail for ID: {pack_id}")
            
            # Get the graphic pack
            try:
                pack = GraphicPack.objects.get(id=pack_id)
                logger.info(f"Found graphic pack: {pack.name}")
                
                # Get templates directly
                templates = Template.objects.filter(graphic_pack=pack)
                logger.info(f"Found {templates.count()} templates for pack {pack_id}")
                
                template_data = []
                for template in templates:
                    template_config = template.template_config or {}
                    elements = template_config.get('elements', {})
                    template_data.append({
                        'id': template.id,
                        'content_type': template.content_type,
                        'elements_count': len(elements),
                        'template_config': template_config,
                        'elements': [
                            {
                                'key': key,
                                'type': element.get('type', 'text'),
                                'position': element.get('position', {}),
                                'style': element.get('style', {})
                            } for key, element in elements.items()
                        ]
                    })
                
                return Response({
                    'pack_id': pack_id,
                    'pack_name': pack.name,
                    'templates_count': templates.count(),
                    'templates': template_data,
                    'raw_templates': list(templates.values('id', 'content_type', 'graphic_pack_id'))
                })
                
            except GraphicPack.DoesNotExist:
                return Response({
                    'error': f'Graphic pack with ID {pack_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error in TestGraphicPackDetailView: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to test graphic pack detail: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )