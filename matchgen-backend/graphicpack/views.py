import logging
import time
from io import BytesIO
from typing import Dict, Any
from datetime import datetime

import cloudinary.uploader
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
import os
from django.conf import settings
from django.db.models import Q
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import Club
from content.models import Match
from users.permissions import HasFeaturePermission, FeaturePermission

from .models import GraphicPack, Template, TextElement, MediaItem
from .serializers import GraphicPackSerializer, TextElementSerializer, MediaItemSerializer

logger = logging.getLogger(__name__)


def apply_image_color_modifications(img, element):
    """Apply color modifications to an image based on element settings."""
    if element.image_color_filter == 'none':
        return img

    # Apply brightness, contrast, and saturation adjustments
    if element.image_brightness != 1.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(element.image_brightness)

    if element.image_contrast != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(element.image_contrast)

    if element.image_saturation != 1.0:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(element.image_saturation)

    # Apply color filters
    if element.image_color_filter == 'grayscale':
        img = img.convert('L').convert('RGBA')
    elif element.image_color_filter == 'sepia':
        # Convert to grayscale first, then apply sepia effect
        img_gray = img.convert('L')
        img_sepia = Image.new('RGB', img_gray.size)
        for x in range(img_gray.width):
            for y in range(img_gray.height):
                pixel = img_gray.getpixel((x, y))
                # Sepia formula
                r = min(255, int(pixel * 0.393 + pixel * 0.769 + pixel * 0.189))
                g = min(255, int(pixel * 0.349 + pixel * 0.686 + pixel * 0.168))
                b = min(255, int(pixel * 0.272 + pixel * 0.534 + pixel * 0.131))
                img_sepia.putpixel((x, y), (r, g, b))
        img = img_sepia.convert('RGBA')
    elif element.image_color_filter == 'invert':
        img = ImageOps.invert(img.convert('RGB')).convert('RGBA')
    elif element.image_color_filter == 'custom':
        # Apply custom color tint
        try:
            # Parse hex color
            tint_color = element.image_color_tint.lstrip('#')
            r = int(tint_color[0:2], 16)
            g = int(tint_color[2:4], 16)
            b = int(tint_color[4:6], 16)

            # Create a tint overlay
            tint_overlay = Image.new('RGBA', img.size, (r, g, b, 128))
            img = Image.alpha_composite(img, tint_overlay)
        except (ValueError, IndexError):
            logger.warning(f"Invalid tint color: {element.image_color_tint}")

    return img


def get_font(font_family, font_size, font_weight='normal'):
    """Get a font with the specified family, size, and weight."""
    try:
        # Try to load the specified font family
        if font_family.lower() == 'arial':
            # Try system Arial font
            font_paths = [
                '/System/Library/Fonts/Arial.ttf',  # macOS
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
                'C:/Windows/Fonts/arial.ttf',  # Windows
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, font_size)
        
        # Try to load from Cloudinary or other sources
        # For now, fall back to default font
        return ImageFont.load_default()
        
    except Exception as e:
        logger.warning(f"Failed to load font {font_family}: {str(e)}")
        return ImageFont.load_default()


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


def get_font(font_family, font_size):
    """
    Load a TrueType font by name and size.
    Tries Cloudinary first, then system fonts, then falls back to default.
    """
    try:
        # Map font_family to Cloudinary URLs or system paths
        font_map = {
            "Arial": "https://res.cloudinary.com/dxoxuyz0j/raw/upload/v1/fonts/arial.ttf",
            "Roboto": "https://res.cloudinary.com/dxoxuyz0j/raw/upload/v1/fonts/Roboto-Regular.ttf",
            "Montserrat": "https://res.cloudinary.com/dxoxuyz0j/raw/upload/v1755936573/Montserrat-BlackItalic_pizq8t.ttf",
            "DejaVuSans": "https://res.cloudinary.com/dxoxuyz0j/raw/upload/v1/fonts/DejaVuSans.ttf",
            "Dana": "https://res.cloudinary.com/dxoxuyz0j/raw/upload/v1759506430/DANA-REGULAR_neadc4.OTF",
            "Quickly": "https://res.cloudinary.com/dxoxuyz0j/raw/upload/v1759674589/QUICKING-REGULAR_wsvwv0.OTF"
        }
        
        logger.info(f"🎯 Requesting font: {font_family} with size {font_size}")
        logger.info(f"🎯 Available fonts: {list(font_map.keys())}")
        
        # Get the static fonts directory
        static_fonts_dir = os.path.join(settings.BASE_DIR, 'static', 'fonts')
        
        # Define font paths to try (Cloudinary first, then system fonts)
        font_paths = [
            # Cloudinary fonts (if available)
            font_map.get(font_family, font_map["Roboto"]),
            # System fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
            # Project fonts
            os.path.join(static_fonts_dir, "Roboto-Regular.ttf"),
            os.path.join(static_fonts_dir, "DejaVuSans.ttf"),
            os.path.join(static_fonts_dir, "Arial.ttf"),
            os.path.join(static_fonts_dir, "Montserrat-BlackItalic_pizq8t.ttf"),
        ]
        
        # Try to load the font
        for font_path in font_paths:
            try:
                if font_path.startswith('http'):
                    # Download font from Cloudinary/URL
                    logger.info(f"🔄 Downloading font from {font_path}")
                    response = requests.get(font_path, timeout=10)
                    response.raise_for_status()
                    
                    logger.info(f"📦 Downloaded {len(response.content)} bytes from Cloudinary")
                    
                    # Create font from bytes
                    font = ImageFont.truetype(BytesIO(response.content), font_size)
                    logger.info(f"✅ SUCCESS: Loaded font from Cloudinary with size {font_size}")
                    return font
                else:
                    # Load from local path
                    font = ImageFont.truetype(font_path, font_size)
                    logger.info(f"✅ SUCCESS: Loaded font from {font_path} with size {font_size}")
                    return font
                    
            except Exception as e:
                logger.warning(f"❌ Failed to load font from {font_path}: {e}")
                continue
        
        # Fallback to default font
        logger.warning(f"❌ WARNING: No TrueType font could be loaded. Falling back to default font, which ignores font_size={font_size}")
        return ImageFont.load_default()
        
    except Exception as e:
        logger.warning(f"❌ Font loading error, using default font: {e}")
        return ImageFont.load_default()


class MatchdayPostGenerator(APIView):
    """Generate a Matchday social media post from a selected fixture."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate a matchday post for a specific fixture."""
        try:
            logger.info(f"MatchdayPostGenerator called with data: {request.data}")
            
            match_id = request.data.get("match_id")
            if not match_id:
                logger.error("No match_id provided in request")
                return Response(
                    {"error": "match_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Processing match_id: {match_id}")

            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
                logger.info(f"Found club: {club.name} (ID: {club.id})")
            except Club.DoesNotExist:
                logger.error(f"No club found for user: {request.user.email}")
                return Response(
                    {"error": "Club not found for this user."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check if club has selected a graphic pack
            if not club.selected_pack:
                logger.error(f"No graphic pack selected for club: {club.name}")
                return Response(
                    {"error": "No graphic pack selected for this club."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if the selected pack actually exists
            try:
                selected_pack = GraphicPack.objects.get(id=club.selected_pack.id)
                logger.info(f"Club selected pack: {selected_pack.name} (ID: {selected_pack.id})")
            except GraphicPack.DoesNotExist:
                logger.error(f"Selected pack ID {club.selected_pack.id} does not exist in database")
                return Response(
                    {"error": f"Selected graphic pack (ID: {club.selected_pack.id}) no longer exists in database."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get the match
            try:
                match = Match.objects.get(id=match_id, club=club)
                logger.info(f"Found match: {match.opponent} vs {match.club.name}")
            except Match.DoesNotExist:
                logger.error(f"Match with ID {match_id} not found for club {club.name}")
                return Response(
                    {"error": "Match not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get the matchday template using raw SQL to avoid column issues
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, content_type, sport, graphic_pack_id, image_url
                        FROM graphicpack_template 
                        WHERE graphic_pack_id = %s AND content_type = 'matchday'
                    """, [selected_pack.id])
                    template_data = cursor.fetchone()
                    
                if template_data:
                    template_id, content_type, sport, graphic_pack_id, image_url = template_data
                    logger.info(f"Found matchday template: {template_id}")
                    
                    # Create a minimal template object with the data we need
                    class MinimalTemplate:
                        def __init__(self, id, content_type, sport, graphic_pack_id, image_url):
                            self.id = id
                            self.content_type = content_type
                            self.sport = sport
                            self.graphic_pack_id = graphic_pack_id
                            self.image_url = image_url
                            self.template_config = {}  # Default empty config
                    
                    template = MinimalTemplate(template_id, content_type, sport, graphic_pack_id, image_url)
                else:
                    logger.error(f"No matchday template found for graphic pack {selected_pack.name}")
                    return Response(
                        {"error": "Matchday template not found for this club's graphic pack."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            except Exception as e:
                logger.error(f"Error getting matchday template: {str(e)}")
                return Response(
                    {"error": "Error retrieving matchday template."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Generate the matchday post
            logger.info("Starting matchday post generation...")
            result = self._generate_matchday_post(match, template, club, selected_pack)
            
            if result.get("error"):
                logger.error(f"Error in _generate_matchday_post: {result.get('error')}")
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            logger.info("Matchday post generated successfully")
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating matchday post: {str(e)}", exc_info=True)
            return Response(
                {"error": f"An error occurred while generating the matchday post: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



    def _generate_matchday_post(self, match: Match, template: Template, club: Club, selected_pack: GraphicPack) -> Dict[str, Any]:
        """Generate a matchday post with fixture details overlaid on template."""
        logger.info(f"Generating matchday post for match {match.id}, club {club.name}")
        
        # Load the template image
        try:
            response = requests.get(template.image_url, timeout=30)
            response.raise_for_status()
            base_image = Image.open(BytesIO(response.content)).convert("RGBA")
            logger.info(f"Template image loaded, dimensions: {base_image.size}")
        except Exception as e:
            logger.error(f"Error loading template image: {str(e)}")
            return {"error": f"Failed to load template image: {str(e)}"}

        # Create drawing context
        draw = ImageDraw.Draw(base_image)
        
        # Prepare fixture data
        fixture_data = self._prepare_fixture_data(match)
        
        # Get text elements from database
        try:
            text_elements = TextElement.objects.filter(
                graphic_pack=selected_pack,
                content_type='matchday'
            )
            logger.info(f"Found {text_elements.count()} text elements for graphic pack {selected_pack.id}")
            
        except Exception as e:
            logger.error(f"Error getting text elements: {str(e)}")
            return {"error": f"Failed to get text elements: {str(e)}"}
        
        # Render each element (text or image)
        for text_element in text_elements:
            # Get the value for this element
            value = fixture_data.get(text_element.element_name, "")
            if not value:
                logger.info(f"Skipping {text_element.element_name} - no value available")
                continue
                
            logger.info(f"Processing element: {text_element.element_name} (type: {text_element.element_type}) = '{value}'")
            
            # Auto-detect image elements by checking if content is a URL and element_name contains 'logo'
            if text_element.element_name in ['opponent_logo', 'club_logo'] and value.startswith('http'):
                logger.info(f"Auto-detected image element: {text_element.element_name} (URL detected)")
                text_element.element_type = 'image'
            
            if text_element.element_type == 'text':
                logger.info(f"Rendering TEXT element: {text_element.element_name}")
                try:
                    # Get font settings directly from TextElement
                    font_size = text_element.font_size
                    font_family = text_element.font_family
                    font_color = text_element.font_color
                    position_x = text_element.position_x
                    position_y = text_element.position_y
                    alignment = text_element.alignment
                    
                    logger.info(f"Font settings: size={font_size}, family={font_family}, color={font_color}, pos=({position_x},{position_y})")
                    
                    # Load font using the dedicated function
                    font = get_font(font_family, font_size)
                    
                    # Calculate anchor point for precise positioning
                    if alignment == 'center':
                        anchor = 'mm'  # middle-middle (center horizontally and vertically)
                    elif alignment == 'right':
                        anchor = 'rm'  # right-middle (right-aligned, middle vertically)
                    else:  # left
                        anchor = 'lm'  # left-middle (left-aligned, middle vertically)
                    
                    # Draw the text with anchor point for precise positioning
                    draw.text((position_x, position_y), value, font=font, fill=font_color, anchor=anchor)
                    
                    logger.info(f"Rendered text '{value}' at ({position_x}, {position_y}) with anchor '{anchor}' and size {font_size}")
                    
                except Exception as e:
                    logger.error(f"Error rendering text element {text_element.element_name}: {str(e)}")
                    continue
                    
            elif text_element.element_type == 'image':
                logger.info(f"Rendering IMAGE element: {text_element.element_name}")
                try:
                    # Download the image
                    response = requests.get(value)
                    response.raise_for_status()
                    
                    # Load the image
                    img = Image.open(BytesIO(response.content))
                    logger.info(f"Image downloaded successfully: {img.size}")
                    
                    # Resize image if needed
                    if hasattr(text_element, 'image_width') and hasattr(text_element, 'image_height') and text_element.image_width and text_element.image_height:
                        if hasattr(text_element, 'maintain_aspect_ratio') and text_element.maintain_aspect_ratio:
                            # Calculate aspect ratio
                            img_ratio = img.width / img.height
                            target_ratio = text_element.image_width / text_element.image_height
                            
                            if img_ratio > target_ratio:
                                # Image is wider, fit to width
                                new_width = text_element.image_width
                                new_height = int(text_element.image_width / img_ratio)
                            else:
                                # Image is taller, fit to height
                                new_height = text_element.image_height
                                new_width = int(text_element.image_height * img_ratio)
                        else:
                            new_width = text_element.image_width
                            new_height = text_element.image_height
                        
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        logger.info(f"Image resized to: {img.size}")
                    
                    # Apply color modifications if specified
                    if hasattr(text_element, 'image_color_filter') and text_element.image_color_filter != 'none':
                        img = apply_image_color_modifications(img, text_element)
                        logger.info(f"Image after color modifications: {img.size}")
                    
                    # Calculate position
                    x = text_element.position_x
                    y = text_element.position_y
                    
                    # Only use home/away positioning for specific elements that need it
                    # (like logos), not for general text elements like lineups
                    should_use_home_away = text_element.element_name in ['club_logo', 'opponent_logo', 'player_image', 'photo_image']
                    
                    # Use home/away specific positioning if available
                    if hasattr(match, 'home_away') and match.home_away and should_use_home_away:
                        if match.home_away == 'HOME' and text_element.home_position_x is not None and text_element.home_position_x != 0:
                            x = text_element.home_position_x
                            y = text_element.home_position_y
                        elif match.home_away == 'AWAY' and text_element.away_position_x is not None and text_element.away_position_x != 0:
                            x = text_element.away_position_x
                            y = text_element.away_position_y
                    
                    # Calculate paste position to center the image
                    paste_x = x - img.width // 2
                    paste_y = y - img.height // 2
                    
                    # Convert to RGBA if needed
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    # Paste the image onto the base image
                    base_image.paste(img, (paste_x, paste_y), img)
                    logger.info(f"Image pasted at ({paste_x}, {paste_y})")
                    
                except Exception as e:
                    logger.error(f"Failed to render image element {text_element.element_name}: {str(e)}")
                    continue
            else:
                logger.warning(f"Unknown element type: {text_element.element_type} for element {text_element.element_name}")

        # Save to buffer with high resolution
        buffer = BytesIO()
        base_image.save(buffer, format="PNG", quality=95)
        buffer.seek(0)

        # Upload to Cloudinary
        try:
            logger.info("Uploading image to Cloudinary...")
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
            logger.info(f"Image uploaded successfully to Cloudinary: {image_url}")
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {str(e)}")
            return {"error": f"Failed to upload image to Cloudinary: {str(e)}"}

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
            # Extract just the date part and format it
            date_only = match.date.date()
            date_str = date_only.strftime("%d/%m/%y")
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
        
        # Get opponent logo URL from the match model
        opponent_logo_url = match.opponent_logo or ""
        
        # Get club logo URL from the club model
        club_logo_url = match.club.logo if match.club and match.club.logo else ""
        
        # Get home/away status from the match model
        home_away = match.home_away if hasattr(match, 'home_away') and match.home_away else "HOME"
        
        # Base fixture data
        fixture_data = {
            "date": date_str,
            "time": time_str,
            "venue": venue_str,
            "opponent": opponent_str,
            "opponent_logo": opponent_logo_url,  # Add opponent logo URL
            "club_logo": club_logo_url,  # Add club logo URL
            "home_away": home_away,
            "club_name": match.club.name if match.club else "Club"
        }
        
        # Add text alternatives when logos are not available
        if not opponent_logo_url or opponent_logo_url == "":
            fixture_data["opponent_text"] = opponent_str  # Use opponent name as text alternative
            logger.info(f"Opponent logo not available, using opponent_text: '{opponent_str}'")
        else:
            fixture_data["opponent_text"] = ""  # Empty when logo is available
        
        if not club_logo_url or club_logo_url == "":
            fixture_data["club_logo_alt"] = match.club.name if match.club else "Club"  # Use club name as text alternative
            logger.info(f"Club logo not available, using club_logo_alt: '{match.club.name if match.club else 'Club'}'")
        else:
            fixture_data["club_logo_alt"] = ""  # Empty when logo is available
        
        return fixture_data


class SocialMediaPostGenerator(APIView):
    """Generic social media post generator that handles all post types."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, post_type='matchday'):
        """Test endpoint to verify URL is accessible."""
        return Response({
            "message": f"SocialMediaPostGenerator endpoint is accessible for post_type: {post_type}",
            "post_type": post_type,
            "url": request.path,
            "method": request.method
        }, status=status.HTTP_200_OK)
    
    def post(self, request, post_type='matchday'):
        logger.info(f"SocialMediaPostGenerator called with post_type: {post_type}")
        logger.info(f"Request URL: {request.path}")
        logger.info(f"Request method: {request.method}")
        # Map post types to feature codes
        feature_mapping = {
            'matchday': 'post.matchday',
            'upcomingFixture': 'post.upcoming',
            'startingXI': 'post.startingxi',
            'goal': 'post.goal',
            'sub': 'post.substitution',
            'player': 'post.potm',
            'halftime': 'post.halftime',
            'fulltime': 'post.fulltime'
        }
        
        # Check feature access
        feature_code = feature_mapping.get(post_type)
        if feature_code:
            try:
                club = Club.objects.get(user=request.user)
                if not FeaturePermission.has_feature_access(request.user, club, feature_code):
                    return Response({
                        "error": f"Feature '{post_type}' is not available in your current subscription tier",
                        "feature_code": feature_code,
                        "upgrade_required": True
                    }, status=status.HTTP_403_FORBIDDEN)
            except Club.DoesNotExist:
                return Response({
                    "error": "No club found for this user"
                }, status=status.HTTP_404_NOT_FOUND)
        try:
            logger.info(f"SocialMediaPostGenerator called for post type: {post_type}")
            
            # Validate post type
            valid_post_types = [
                'matchday', 'upcomingFixture', 'startingXI', 'goal', 
                'sub', 'player', 'halftime', 'fulltime'
            ]
            
            if post_type not in valid_post_types:
                return Response({
                    "error": f"Invalid post type: {post_type}. Valid types: {valid_post_types}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get match_id from request
            match_id = request.data.get('match_id')
            if not match_id:
                logger.error("No match_id provided in request")
                return Response({
                    "error": "match_id is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Processing match_id: {match_id}")
            
            # Get the match
            try:
                match = Match.objects.get(id=match_id)
            except Match.DoesNotExist:
                return Response({
                    "error": f"Match with id {match_id} not found"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response({
                    "error": "No club found for this user"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get the club's selected graphic pack
            pack = club.selected_pack
            if not pack:
                return Response({
                    "error": "No graphic pack selected for this club"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Found club: {club.name} (ID: {club.id})")
            logger.info(f"Club selected pack: {pack.name} (ID: {pack.id})")
            logger.info(f"Found match: {match.opponent} vs {match.club.name}")
            
            # Get the template for this post type (case-insensitive lookup)
            logger.info(f"Looking for template with graphic_pack={pack.id} and content_type='{post_type}'")
            try:
                # Try exact match first
                template = Template.objects.get(
                    graphic_pack=pack,
                    content_type=post_type
                )
                logger.info(f"Found {post_type} template (exact match): {template.id}")
            except Template.DoesNotExist:
                # Try case-insensitive lookup
                try:
                    template = Template.objects.get(
                        graphic_pack=pack,
                        content_type__iexact=post_type
                    )
                    logger.info(f"Found {post_type} template (case-insensitive match): {template.id}")
                except Template.DoesNotExist:
                    # Check what templates exist for this pack
                    existing_templates = Template.objects.filter(graphic_pack=pack)
                    existing_content_types = [t.content_type for t in existing_templates]
                    logger.error(f"No {post_type} template found (exact or case-insensitive). Available templates for pack {pack.id}: {existing_content_types}")
                    return Response({
                        "error": f"No {post_type} template found in selected graphic pack",
                        "available_templates": existing_content_types,
                        "graphic_pack_id": pack.id,
                        "graphic_pack_name": pack.name
                    }, status=status.HTTP_404_NOT_FOUND)
            
            logger.info(f"Starting {post_type} post generation...")
            logger.info(f"=== {post_type.upper()} POST GENERATION STARTED ===")
            logger.info(f"Generating {post_type} post for match {match_id}, club {club.name}")
            logger.info(f"Template image URL: {template.image_url}")
            logger.info(f"Selected pack: {pack.name} (ID: {pack.id})")
            
            # Generate the post
            try:
                image_url = self._generate_social_media_post(match, club, pack, template, post_type, request)
                
                logger.info(f"{post_type.capitalize()} post generated successfully")
                
                return Response({
                    "success": True,
                    "image_url": image_url,
                    "post_type": post_type,
                    "match_id": match_id,
                    "club_name": club.name,
                    "fixture_details": self._prepare_fixture_data(match)
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error generating {post_type} post: {str(e)}", exc_info=True)
                return Response({
                    "error": f"Failed to generate {post_type} post: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in SocialMediaPostGenerator: {str(e)}", exc_info=True)
            return Response({
                "error": f"Internal server error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generate_social_media_post(self, match, club, pack, template, post_type, request=None):
        """Generate a social media post for the specified post type."""
        logger.info(f"=== {post_type.upper()} POST GENERATION STARTED ===")
        logger.info(f"Generating {post_type} post for match {match.id}, club {club.name}")
        logger.info(f"Template image URL: {template.image_url}")
        logger.info(f"Selected pack: {pack.name} (ID: {pack.id})")
        
        # Fetch template image
        logger.info("Fetching template image from URL...")
        try:
            response = requests.get(template.image_url)
            response.raise_for_status()
            logger.info(f"Template image fetched successfully, size: {len(response.content)} bytes")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch template image: {str(e)}")
            raise Exception(f"Failed to fetch template image: {str(e)}")
        
        # Load template image
        try:
            template_image = Image.open(BytesIO(response.content))
            logger.info(f"Template image loaded, dimensions: {template_image.size}")
        except Exception as e:
            logger.error(f"Failed to load template image: {str(e)}")
            raise Exception(f"Failed to load template image: {str(e)}")
        
        # Get text elements for this post type
        logger.info("=== TEXT ELEMENT LOOKUP STARTED ===")
        text_elements = TextElement.objects.filter(
            graphic_pack=pack,
            content_type=post_type
        )
        
        logger.info(f"Total text elements in database: {TextElement.objects.count()}")
        logger.info(f"Found {text_elements.count()} text elements for graphic pack {pack.id}")
        
        # Prepare fixture data
        fixture_data = self._prepare_fixture_data(match, post_type)
        
        # Handle substitution-specific data from request
        if post_type == 'sub' and request:
            # Get substitution data from request - support multiple substitutions
            substitutions = request.data.get('substitutions', [])
            minute = request.data.get('minute', 'Minute')
            
            # Check for new direct format first
            players_on = request.data.get('players_on', [])
            players_off = request.data.get('players_off', [])
            
            if players_on or players_off:
                # New flexible format - handle multiple players independently
                logger.info(f"Using new flexible substitution format: {len(players_on)} players on, {len(players_off)} players off")
                
                # Format players as multiline text
                players_on_text = '\n'.join(players_on) if players_on else "Player On"
                players_off_text = '\n'.join(players_off) if players_off else "Player Off"
                
                # Create substitution display text
                substitution_texts = []
                if players_off and players_on:
                    # Show all combinations
                    for off_player in players_off:
                        for on_player in players_on:
                            substitution_texts.append(f"{off_player} → {on_player} ({minute}')")
                elif players_off:
                    # Only players going off
                    for off_player in players_off:
                        substitution_texts.append(f"{off_player} → (Substitution) ({minute}')")
                elif players_on:
                    # Only players coming on
                    for on_player in players_on:
                        substitution_texts.append(f"(Substitution) → {on_player} ({minute}')")
                
                fixture_data.update({
                    "player_on": players_on_text,
                    "player_off": players_off_text, 
                    "minute": minute,
                    "substitutions": "\n".join(substitution_texts)  # All substitutions as text
                })
                
                logger.info(f"Substitution data: players_on={players_on_text}, players_off={players_off_text}")
            elif substitutions:
                # Legacy format - handle old substitution pairs
                players_on = [sub.get('player_on', '') for sub in substitutions if sub.get('player_on')]
                players_off = [sub.get('player_off', '') for sub in substitutions if sub.get('player_off')]
                
                # Pair them up (assuming they're in order)
                substitution_texts = []
                for i in range(min(len(players_on), len(players_off))):
                    substitution_texts.append(f"{players_off[i]} → {players_on[i]} ({minute}')")
                    logger.info(f"Substitution {i+1}: {players_off[i]} → {players_on[i]} ({minute}')")
                
                # Update fixture data with substitution-specific values
                # Format players as multiline text like Starting XI does
                players_on_text = '\n'.join(players_on) if players_on else "Player On"
                players_off_text = '\n'.join(players_off) if players_off else "Player Off"
                
                fixture_data.update({
                    "player_on": players_on_text,
                    "player_off": players_off_text, 
                    "minute": minute,
                    "substitutions": "\n".join(substitution_texts)  # All substitutions as text
                })
            else:
                # Fallback to single substitution format for backward compatibility
                player_on = request.data.get('player_on', 'Player On')
                player_off = request.data.get('player_off', 'Player Off')
                minute = request.data.get('minute', 'Minute')
                
                fixture_data.update({
                    "player_on": player_on,
                    "player_off": player_off,
                    "minute": minute,
                    "substitutions": f"{player_off} → {player_on} ({minute}')"
                })
                
                logger.info(f"Single substitution data: Player On={player_on}, Player Off={player_off}, Minute={minute}")
        
        # Handle halftime score data from request
        if post_type == 'halftime' and request:
            # Get halftime score data from request
            home_score_ht = request.data.get('home_score_ht', '0')
            away_score_ht = request.data.get('away_score_ht', '0')
            
            # Update fixture data with halftime score values
            fixture_data.update({
                "home_score_ht": home_score_ht,
                "away_score_ht": away_score_ht
            })
            
            logger.info(f"Halftime score data: Home={home_score_ht}, Away={away_score_ht}")
        
        # Handle fulltime score data from request
        if post_type == 'fulltime' and request:
            # Get fulltime score data from request
            home_score_ft = request.data.get('home_score_ft', '0')
            away_score_ft = request.data.get('away_score_ft', '0')
            
            # Update fixture data with fulltime score values
            fixture_data.update({
                "home_score_ft": home_score_ft,
                "away_score_ft": away_score_ft
            })
            
            logger.info(f"Fulltime score data: Home={home_score_ft}, Away={away_score_ft}")
        
        # Handle starting XI data from request
        if post_type == 'startingXI' and request:
            # Get starting XI data from request
            starting_lineup = request.data.get('starting_lineup', [])
            substitutes = request.data.get('substitutes', [])
            
            # Format as lists for display
            starting_lineup_text = '\n'.join([f"{player}" for player in starting_lineup]) if starting_lineup else "Starting XI TBC"
            substitutes_text = '\n'.join([f"{player}" for player in substitutes]) if substitutes else "Substitutes TBC"
            
            # Update fixture data with starting XI values
            fixture_data.update({
                "starting_lineup": starting_lineup_text,
                "substitutes": substitutes_text
            })
            
            logger.info(f"Starting XI data: {len(starting_lineup)} starters, {len(substitutes)} substitutes")
        
        # Handle goal data from request
        if post_type == 'goal' and request:
            # Get goal data from request
            goal_scorer = request.data.get('goal_scorer', 'Player Name')
            goal_minute = request.data.get('goal_minute', 'Minute')
            
            # Update fixture data with goal values
            fixture_data.update({
                "player_name": goal_scorer,
                "goal_minute": goal_minute
            })
            
            logger.info(f"Goal data: scorer={goal_scorer}, minute={goal_minute}")
        
        # Create a copy of the template image to work with
        base_image = template_image.copy()
        
        # Process text elements
        elements_to_render = []
        for element in text_elements:
            logger.info(f"Processing element: {element.element_name} (type: {element.element_type}) - size: {element.font_size}, position: ({element.position_x}, {element.position_y})")
            
            # Get the content for this element
            content = fixture_data.get(element.element_name, '')
            logger.info(f"Content for {element.element_name}: '{content}'")
            
            # Auto-detect image elements by checking if content is a URL and element_name contains 'logo'
            if element.element_name in ['opponent_logo', 'club_logo'] and content.startswith('http'):
                logger.info(f"Auto-detected image element: {element.element_name} (URL detected)")
                element.element_type = 'image'
            
            if content:
                elements_to_render.append(element.element_name)
                
                if element.element_type == 'text':
                    logger.info(f"Rendering TEXT element: {element.element_name}")
                    # Render text element
                    self._render_text_element(base_image, element, content, match)
                elif element.element_type == 'image':
                    logger.info(f"Rendering IMAGE element: {element.element_name}")
                    # Render image element
                    self._render_image_element(base_image, element, content, match)
                else:
                    logger.warning(f"Unknown element type: {element.element_type} for element {element.element_name}")
            else:
                logger.info(f"No content found for element: {element.element_name}")
        
        logger.info(f"Rendering {len(elements_to_render)} text elements")
        logger.info(f"Elements to render: {elements_to_render}")
        
        # Save the generated image
        timestamp = int(time.time())
        filename = f"{post_type}_posts/club_{club.id}/{post_type}_{match.id}_{timestamp}.png"
        
        logger.info(f"Uploading image to Cloudinary...")
        try:
            # Convert PIL image to bytes
            img_buffer = BytesIO()
            base_image.save(img_buffer, format='PNG', quality=95)
            img_buffer.seek(0)
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                img_buffer,
                public_id=filename,
                folder="matchgen",
                overwrite=True,
                resource_type="image"
            )
            
            image_url = result['secure_url']
            logger.info(f"Image uploaded successfully to Cloudinary: {image_url}")
            
        except Exception as e:
            logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
            raise Exception(f"Failed to upload image: {str(e)}")
        
        logger.info(f"{post_type.capitalize()} post generated successfully")
        return image_url
    
    def _render_text_element(self, base_image, element, content, match):
        """Render a text element on the base image."""
        logger.info(f"Rendering text element: {element.element_name} = '{content}'")
        
        # Get font settings directly from TextElement fields
        font_size = element.font_size
        font_family = element.font_family
        font_color = element.font_color
        alignment = element.alignment  # For positioning
        text_alignment = getattr(element, 'text_alignment', element.alignment)  # For text alignment within element
        
        logger.info(f"=== FONT SIZE DEBUG ===")
        logger.info(f"Font size: {font_size}")
        logger.info(f"Font family: {font_family}")
        logger.info(f"Font color: {font_color}")
        logger.info(f"Alignment: {alignment}")
        logger.info(f"Font size type: {type(font_size)}")
        logger.info(f"Font size value: {font_size}")
        
        # Load font
        logger.info(f"=== FONT LOADING DEBUG ===")
        logger.info(f"Attempting to load font with size: {font_size}")
        
        try:
            font = get_font(font_family, font_size)
            logger.info(f"Font loaded successfully: {font}")
        except Exception as e:
            logger.warning(f"FAILED: Using default font - size {font_size} may not be applied correctly")
            logger.info(f"Default font object: {font}")
        
        # Calculate position
        x = element.position_x
        y = element.position_y
        
        # Use home/away specific positioning if available
        logger.info(f"=== HOME/AWAY POSITIONING DEBUG ===")
        logger.info(f"Match home_away: {getattr(match, 'home_away', 'Not set')}")
        logger.info(f"Element home_position_x: {getattr(element, 'home_position_x', 'Not set')}")
        logger.info(f"Element away_position_x: {getattr(element, 'away_position_x', 'Not set')}")
        logger.info(f"Default position: ({x}, {y})")
        
        # Only use home/away positioning for specific elements that need it
        # (like logos), not for general text elements like lineups
        should_use_home_away = element.element_name in ['club_logo', 'opponent_logo', 'player_image', 'photo_image']
        
        if hasattr(match, 'home_away') and match.home_away and should_use_home_away:
            if match.home_away == 'HOME' and element.home_position_x is not None and element.home_position_x != 0:
                x = element.home_position_x
                y = element.home_position_y
                logger.info(f"Using HOME position: ({x}, {y})")
            elif match.home_away == 'AWAY' and element.away_position_x is not None and element.away_position_x != 0:
                x = element.away_position_x
                y = element.away_position_y
                logger.info(f"Using AWAY position: ({x}, {y})")
            else:
                logger.info(f"Home/away positions not set or are default values, using default position: ({x}, {y})")
        else:
            if should_use_home_away:
                logger.info(f"No home_away data, using default position: ({x}, {y})")
            else:
                logger.info(f"Element {element.element_name} doesn't need home/away positioning, using default position: ({x}, {y})")
        
        # Create drawing object
        draw = ImageDraw.Draw(base_image)
        
        # Check if content is multiline
        is_multiline = '\n' in content
        
        if is_multiline:
            # For multiline text, we need to handle positioning manually
            logger.info(f"Rendering multiline text: {element.element_name}")
            
            # Split content into lines
            lines = content.split('\n')
            
            # Calculate line height (approximate)
            line_height = font_size + 5  # Add some spacing between lines
            
            # Get position_anchor for multiline text positioning
            position_anchor = getattr(element, 'position_anchor', 'top')  # Default to top if not set
            logger.info(f"MULTILINE DEBUG - Position anchor: {position_anchor}")
            
            # Calculate starting Y position based on alignment and position_anchor
            if alignment == 'left':
                # Left-aligned multiline text
                for i, line in enumerate(lines):
                    if line.strip():  # Only render non-empty lines
                        if position_anchor == 'top':
                            line_y = y + (i * line_height)
                        elif position_anchor == 'center':
                            # Center anchor - position text block so it's centered around y
                            total_height = len(lines) * line_height
                            line_y = y - (total_height // 2) + (i * line_height)
                        else:  # bottom anchor - calculate so last line is at y
                            # Calculate total height of all lines
                            total_height = len(lines) * line_height
                            # Position so the bottom line is at y
                            line_y = y - total_height + (i * line_height)
                        draw.text((x, line_y), line, font=font, fill=font_color)
                        logger.info(f"Rendered line {i+1}: '{line}' at ({x}, {line_y}) with {position_anchor} anchor")
            elif alignment == 'right':
                # Right-aligned multiline text
                for i, line in enumerate(lines):
                    if line.strip():  # Only render non-empty lines
                        if position_anchor == 'top':
                            line_y = y + (i * line_height)
                        elif position_anchor == 'center':
                            # Center anchor - position text block so it's centered around y
                            total_height = len(lines) * line_height
                            line_y = y - (total_height // 2) + (i * line_height)
                        else:  # bottom anchor - calculate so last line is at y
                            # Calculate total height of all lines
                            total_height = len(lines) * line_height
                            # Position so the bottom line is at y
                            line_y = y - total_height + (i * line_height)
                        # Get text width for right alignment
                        bbox = draw.textbbox((0, 0), line, font=font)
                        text_width = bbox[2] - bbox[0]
                        line_x = x - text_width
                        draw.text((line_x, line_y), line, font=font, fill=font_color)
                        logger.info(f"Rendered line {i+1}: '{line}' at ({line_x}, {line_y}) with {position_anchor} anchor")
            else:
                # Center-aligned multiline text
                for i, line in enumerate(lines):
                    if line.strip():  # Only render non-empty lines
                        if position_anchor == 'top':
                            line_y = y + (i * line_height)
                        elif position_anchor == 'center':
                            # Center anchor - position text block so it's centered around y
                            total_height = len(lines) * line_height
                            line_y = y - (total_height // 2) + (i * line_height)
                        else:  # bottom anchor - calculate so last line is at y
                            # Calculate total height of all lines
                            total_height = len(lines) * line_height
                            # Position so the bottom line is at y
                            line_y = y - total_height + (i * line_height)
                        # Get text width for center alignment
                        bbox = draw.textbbox((0, 0), line, font=font)
                        text_width = bbox[2] - bbox[0]
                        line_x = x - (text_width // 2)
                        draw.text((line_x, line_y), line, font=font, fill=font_color)
                        logger.info(f"Rendered line {i+1}: '{line}' at ({line_x}, {line_y}) with {position_anchor} anchor")
        else:
            # Determine anchor point based on alignment and position_anchor for single-line text
            position_anchor = getattr(element, 'position_anchor', 'top')  # Default to top if not set
            
            logger.info(f"RENDERING DEBUG - Element: {element.element_name}")
            logger.info(f"RENDERING DEBUG - Position anchor: {position_anchor}")
            logger.info(f"RENDERING DEBUG - Alignment: {alignment}")
            logger.info(f"RENDERING DEBUG - Position: ({x}, {y})")
            
            if alignment == 'left':
                if position_anchor == 'top':
                    anchor = 'lt'  # left-top anchor
                elif position_anchor == 'center':
                    anchor = 'lm'  # left-middle anchor
                else:  # bottom
                    anchor = 'lb'  # left-bottom anchor
            elif alignment == 'center':
                if position_anchor == 'top':
                    anchor = 'mt'  # middle-top anchor
                elif position_anchor == 'center':
                    anchor = 'mm'  # middle-middle anchor
                else:  # bottom
                    anchor = 'mb'  # middle-bottom anchor
            elif alignment == 'right':
                if position_anchor == 'top':
                    anchor = 'rt'  # right-top anchor
                elif position_anchor == 'center':
                    anchor = 'rm'  # right-middle anchor
                else:  # bottom
                    anchor = 'rb'  # right-bottom anchor
            else:
                if position_anchor == 'top':
                    anchor = 'mt'  # middle-top anchor
                elif position_anchor == 'center':
                    anchor = 'mm'  # middle-middle anchor
                else:  # bottom
                    anchor = 'mb'  # middle-bottom anchor
            
            logger.info(f"RENDERING DEBUG - Final anchor point: '{anchor}'")
            logger.info(f"Using anchor point '{anchor}' for alignment '{alignment}'")
            
            # Render single-line text with anchor
            draw.text(
                (x, y),
                content,
                font=font,
                fill=font_color,
                anchor=anchor
            )
        
        logger.info(f"Rendered '{content}' at ({x}, {y}) with color {font_color}, requested font size {font_size}, actual font: {font}")
    
    def _render_image_element(self, base_image, element, content, match):
        """Render an image element on the base image."""
        logger.info(f"=== IMAGE ELEMENT RENDERING START ===")
        logger.info(f"Element name: {element.element_name}")
        logger.info(f"Element type: {element.element_type}")
        logger.info(f"Content (URL): {content}")
        
        if not content:  # Skip if no image URL
            logger.info("No content provided, skipping image element")
            return
            
        logger.info(f"Rendering image element: {element.element_name} from URL: {content}")
        
        try:
            # Download the image
            response = requests.get(content)
            response.raise_for_status()
            
            # Load the image
            img = Image.open(BytesIO(response.content))
            logger.info(f"Image downloaded successfully: {img.size}")
            
            # Resize image if needed
            if hasattr(element, 'image_width') and hasattr(element, 'image_height') and element.image_width and element.image_height:
                if hasattr(element, 'maintain_aspect_ratio') and element.maintain_aspect_ratio:
                    # Calculate aspect ratio
                    img_ratio = img.width / img.height
                    target_ratio = element.image_width / element.image_height
                    
                    if img_ratio > target_ratio:
                        # Image is wider, fit to width
                        new_width = element.image_width
                        new_height = int(element.image_width / img_ratio)
                    else:
                        # Image is taller, fit to height
                        new_height = element.image_height
                        new_width = int(element.image_height * img_ratio)
                else:
                    new_width = element.image_width
                    new_height = element.image_height
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Image resized to: {img.size}")
            
            # Apply color modifications if specified
            if hasattr(element, 'image_color_filter') and element.image_color_filter != 'none':
                img = apply_image_color_modifications(img, element)
                logger.info(f"Image after color modifications: {img.size}")
            
            # Calculate position
            x = element.position_x
            y = element.position_y
            
            # Use home/away specific positioning if available
            logger.info(f"=== IMAGE HOME/AWAY POSITIONING DEBUG ===")
            logger.info(f"Element: {element.element_name}")
            logger.info(f"Match home_away: {getattr(match, 'home_away', 'Not set')}")
            logger.info(f"Element home_position_x: {getattr(element, 'home_position_x', 'Not set')}")
            logger.info(f"Element away_position_x: {getattr(element, 'away_position_x', 'Not set')}")
            logger.info(f"Default position: ({x}, {y})")
            
            # Only use home/away positioning for specific elements that need it
            # (like logos), not for general text elements like lineups
            should_use_home_away = element.element_name in ['club_logo', 'opponent_logo', 'player_image', 'photo_image']
            
            if hasattr(match, 'home_away') and match.home_away and should_use_home_away:
                if match.home_away == 'HOME' and element.home_position_x is not None and element.home_position_x != 0:
                    x = element.home_position_x
                    y = element.home_position_y
                    logger.info(f"Using HOME position: ({x}, {y})")
                elif match.home_away == 'AWAY' and element.away_position_x is not None and element.away_position_x != 0:
                    x = element.away_position_x
                    y = element.away_position_y
                    logger.info(f"Using AWAY position: ({x}, {y})")
                else:
                    logger.info(f"Home/away positions not set or are default values, using default position: ({x}, {y})")
            else:
                if should_use_home_away:
                    logger.info(f"No home_away data, using default position: ({x}, {y})")
                else:
                    logger.info(f"Element {element.element_name} doesn't need home/away positioning, using default position: ({x}, {y})")
            
            # Calculate paste position to center the image
            paste_x = x - img.width // 2
            paste_y = y - img.height // 2
            
            # Convert to RGBA if needed
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Paste the image onto the base image
            base_image.paste(img, (paste_x, paste_y), img)
            logger.info(f"Image pasted at ({paste_x}, {paste_y})")
            
        except Exception as e:
            logger.error(f"Failed to render image element {element.element_name}: {str(e)}")
            # Continue with other elements instead of failing completely
    
    def _prepare_fixture_data(self, match, post_type=None):
        """Prepare fixture data for text rendering."""
        # Format date
        if match.date:
            # Extract just the date part and format it
            date_only = match.date.date()
            date_str = date_only.strftime("%d/%m/%y")
        else:
            date_str = "Date TBC"
        
        # Format time
        if match.time_start:
            try:
                time_obj = datetime.strptime(str(match.time_start), '%H:%M:%S').time()
                time_str = time_obj.strftime("%H:%M")
            except:
                time_str = str(match.time_start)
        else:
            time_str = "Time TBC"
        
        # Format venue
        venue_str = match.venue or "Venue TBC"
        
        # Format opponent
        opponent_str = match.opponent or "Opponent TBC"
        
        # Get opponent logo URL from the match model
        opponent_logo_url = match.opponent_logo or ""
        
        # Get club logo URL from the club model
        club_logo_url = match.club.logo if match.club and match.club.logo else ""
        
        # Get home/away status from the match model
        home_away = match.home_away if hasattr(match, 'home_away') and match.home_away else "HOME"
        
        # Base fixture data
        fixture_data = {
            "date": date_str,
            "time": time_str,
            "venue": venue_str,
            "opponent": opponent_str,
            "opponent_logo": opponent_logo_url,  # Add opponent logo URL
            "club_logo": club_logo_url,  # Add club logo URL
            "home_away": home_away,
            "club_name": match.club.name if match.club else "Club"
        }
        
        # Add text alternatives when logos are not available
        if not opponent_logo_url or opponent_logo_url == "":
            fixture_data["opponent_text"] = opponent_str  # Use opponent name as text alternative
            logger.info(f"Opponent logo not available, using opponent_text: '{opponent_str}'")
        else:
            fixture_data["opponent_text"] = ""  # Empty when logo is available
        
        if not club_logo_url or club_logo_url == "":
            fixture_data["club_logo_alt"] = match.club.name if match.club else "Club"  # Use club name as text alternative
            logger.info(f"Club logo not available, using club_logo_alt: '{match.club.name if match.club else 'Club'}'")
        else:
            fixture_data["club_logo_alt"] = ""  # Empty when logo is available
        
        # Add substitution-specific data if post type is 'sub'
        if post_type == 'sub':
            # For substitution posts, we'll need to get this data from the request
            # For now, we'll add placeholder values that can be overridden
            fixture_data.update({
                "player_on": "Player On",  # This will be overridden by request data
                "player_off": "Player Off",  # This will be overridden by request data
                "minute": "Minute",  # This will be overridden by request data
                "substitutions": "Player Off → Player On (Minute)"  # This will be overridden by request data
            })
        
        # Add halftime score data if post type is 'halftime'
        if post_type == 'halftime':
            fixture_data.update({
                "home_score_ht": "0",  # This will be overridden by request data
                "away_score_ht": "0"   # This will be overridden by request data
            })
        
        # Add fulltime score data if post type is 'fulltime'
        if post_type == 'fulltime':
            fixture_data.update({
                "home_score_ft": "0",  # This will be overridden by request data
                "away_score_ft": "0"   # This will be overridden by request data
            })
        
        # Add starting XI data if post type is 'startingXI'
        if post_type == 'startingXI':
            fixture_data.update({
                "starting_lineup": "Starting XI TBC",  # This will be overridden by request data
                "substitutes": "Substitutes TBC"       # This will be overridden by request data
            })
        
        return fixture_data


class DebugTemplatesView(APIView):
    """Debug endpoint to check templates and their configuration."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            logger.info("DebugTemplatesView called")
            
            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
                logger.info(f"Found club: {club.name}")
            except Club.DoesNotExist:
                logger.error(f"No club found for user: {request.user.email}")
                return Response({
                    "error": "Club not found for this user."
                }, status=status.HTTP_404_NOT_FOUND)

            # Get all graphic packs
            try:
                packs = GraphicPack.objects.all()
                logger.info(f"Found {packs.count()} graphic packs")
                packs_data = []
                
                for pack in packs:
                    templates = Template.objects.filter(graphic_pack=pack)
                    templates_data = []
                    
                    for template in templates:
                        templates_data.append({
                            "id": template.id,
                            "content_type": template.content_type,
                            "image_url": template.image_url,
                            "sport": template.sport,
                            "template_config": template.template_config,
                            "has_config": bool(template.template_config)
                        })
                    
                    packs_data.append({
                        "id": pack.id,
                        "name": pack.name,
                        "description": pack.description,
                        "is_selected": club.selected_pack == pack if club.selected_pack else False,
                        "templates": templates_data,
                        "templates_count": templates.count()
                    })
            except Exception as e:
                logger.error(f"Error getting graphic packs: {str(e)}")
                packs_data = []

            # Get user's matches
            try:
                matches = Match.objects.filter(club=club)
                logger.info(f"Found {matches.count()} matches for club")
                matches_data = []
                
                for match in matches:
                    matches_data.append({
                        "id": match.id,
                        "opponent": match.opponent,
                        "date": match.date.isoformat() if match.date else None,
                        "time_start": match.time_start,
                        "venue": match.venue
                    })
            except Exception as e:
                logger.error(f"Error getting matches: {str(e)}")
                matches_data = []

            response_data = {
                "user": {
                    "id": request.user.id,
                    "email": request.user.email
                },
                "club": {
                    "id": club.id,
                    "name": club.name,
                    "selected_pack_id": club.selected_pack.id if club.selected_pack else None,
                    "selected_pack_name": club.selected_pack.name if club.selected_pack else None
                },
                "graphic_packs": packs_data,
                "matches": matches_data,
                "matches_count": len(matches_data)
            }
            
            logger.info("DebugTemplatesView completed successfully")
            return Response(response_data)

        except Exception as e:
            logger.error(f"Error in DebugTemplatesView: {str(e)}", exc_info=True)
            return Response({
                "error": f"Failed to debug templates: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestEndpointView(APIView):
    """Simple test endpoint to check if the backend is working."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "status": "success",
            "message": "Backend is working!",
            "timestamp": time.time()
        })

    def put(self, request):
        """Test basic Django functionality without database."""
        try:
            logger.info("Testing basic Django functionality...")
            
            # Test 1: Basic Python operations
            test_list = [1, 2, 3, 4, 5]
            test_sum = sum(test_list)
            
            # Test 2: Import operations
            from django.conf import settings
            debug_mode = settings.DEBUG
            
            # Test 3: Basic string operations
            test_string = "Hello World"
            reversed_string = test_string[::-1]
            
            return Response({
                "status": "success",
                "message": "Basic Django functionality working!",
                "timestamp": time.time(),
                "tests": {
                    "list_sum": test_sum,
                    "debug_mode": debug_mode,
                    "reversed_string": reversed_string
                }
            })
        except Exception as e:
            logger.error(f"Basic functionality test failed: {str(e)}", exc_info=True)
            return Response({
                "status": "error",
                "message": f"Basic functionality test failed: {str(e)}",
                "timestamp": time.time()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request):
        """Test basic database connection without models."""
        try:
            logger.info("Testing basic database connection...")
            
            # Test 1: Basic database connection
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 as test_value")
                result = cursor.fetchone()
                logger.info(f"Database connection test result: {result}")
            
            # Test 2: Check database tables
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE '%graphic%'
                """)
                tables = cursor.fetchall()
                table_names = [table[0] for table in tables]
                logger.info(f"Found graphic tables: {table_names}")
            
            return Response({
                "status": "success",
                "message": "Basic database connection working!",
                "timestamp": time.time(),
                "database_info": {
                    "connection_test": result[0] if result else None,
                    "graphic_tables": table_names
                }
            })
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}", exc_info=True)
            return Response({
                "status": "error",
                "message": f"Database connection test failed: {str(e)}",
                "timestamp": time.time()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """Test if the issue is with the view itself."""
        try:
            logger.info("Testing view functionality...")
            
            # Test 1: Basic Python operations
            test_list = [1, 2, 3, 4, 5]
            test_sum = sum(test_list)
            
            # Test 2: Import operations
            from django.conf import settings
            debug_mode = settings.DEBUG
            
            # Test 3: Basic string operations
            test_string = "Hello World"
            reversed_string = test_string[::-1]
            
            # Test 4: Try to import models without using them
            try:
                from .models import GraphicPack, Template
                models_imported = True
                logger.info("Models imported successfully")
            except Exception as model_error:
                models_imported = False
                logger.error(f"Model import failed: {str(model_error)}")
            
            return Response({
                "status": "success",
                "message": "View functionality working!",
                "timestamp": time.time(),
                "tests": {
                    "list_sum": test_sum,
                    "debug_mode": debug_mode,
                    "reversed_string": reversed_string,
                    "models_imported": models_imported
                }
            })
        except Exception as e:
            logger.error(f"View functionality test failed: {str(e)}", exc_info=True)
            return Response({
                "status": "error",
                "message": f"View functionality test failed: {str(e)}",
                "timestamp": time.time()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Test database operations."""
        try:
            logger.info("Testing database operations...")
            
            # Test 1: Basic Django database connection
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                logger.info(f"Database connection test: {result}")
            
            # Test 2: Check if we can query existing data
            try:
                pack_count = GraphicPack.objects.count()
                logger.info(f"GraphicPack count: {pack_count}")
            except Exception as count_error:
                logger.error(f"GraphicPack count failed: {str(count_error)}")
                return Response({
                    "status": "error",
                    "message": f"GraphicPack count failed: {str(count_error)}",
                    "timestamp": time.time()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            try:
                template_count = Template.objects.count()
                logger.info(f"Template count: {template_count}")
            except Exception as count_error:
                logger.error(f"Template count failed: {str(count_error)}")
                return Response({
                    "status": "error",
                    "message": f"Template count failed: {str(count_error)}",
                    "timestamp": time.time()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Test 3: Try to create a simple graphic pack
            try:
                logger.info("Attempting to create GraphicPack...")
                pack = GraphicPack.objects.create(
                    name='Test Pack',
                    description='Test Description',
                    preview_image_url='https://example.com/test.jpg'
                )
                logger.info(f"Created test pack: {pack.id}")
                
                # Test 4: Try to create a simple template
                try:
                    logger.info("Attempting to create Template...")
                    
                    # Test with empty template_config first
                    template = Template.objects.create(
                        graphic_pack=pack,
                        content_type='matchday',
                        sport='football',
                        image_url='https://example.com/test.jpg',
                        template_config={}
                    )
                    logger.info(f"Created test template with empty config: {template.id}")
                    
                    # Test if we can save a template_config
                    try:
                        template.template_config = {"test": "value"}
                        template.save()
                        logger.info("Successfully saved template_config")
                    except Exception as config_error:
                        logger.error(f"Template config save failed: {str(config_error)}", exc_info=True)
                    
                    # Clean up - delete the test data
                    template.delete()
                    logger.info("Deleted test template")
                except Exception as template_error:
                    logger.error(f"Template creation failed: {str(template_error)}", exc_info=True)
                    # Clean up the pack before returning error
                    pack.delete()
                    return Response({
                        "status": "error",
                        "message": f"Template creation failed: {str(template_error)}",
                        "timestamp": time.time()
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                pack.delete()
                logger.info("Deleted test pack")
                
            except Exception as pack_error:
                logger.error(f"Pack creation failed: {str(pack_error)}", exc_info=True)
                return Response({
                    "status": "error",
                    "message": f"Pack creation failed: {str(pack_error)}",
                    "timestamp": time.time()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                "status": "success",
                "message": "Database operations working!",
                "timestamp": time.time(),
                "current_counts": {
                    "packs": pack_count,
                    "templates": template_count
                }
            })
        except Exception as e:
            logger.error(f"Database test failed: {str(e)}", exc_info=True)
            return Response({
                "status": "error",
                "message": f"Database error: {str(e)}",
                "timestamp": time.time()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateTestDataView(APIView):
    """Create test graphic packs and templates for development."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            logger.info("CreateTestDataView called")
            
            # Get user's club and selected pack
            try:
                club = Club.objects.get(user=request.user)
                logger.info(f"Found club: {club.name}")
                
                if not club.selected_pack:
                    logger.error("Club has no selected pack")
                    return Response({
                        "error": "Club has no selected graphic pack"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                pack = club.selected_pack
                logger.info(f"Using club's selected pack: {pack.name} (ID: {pack.id})")
                
            except Club.DoesNotExist:
                logger.error(f"No club found for user {request.user.email}")
                return Response({
                    "error": "No club found for this user"
                }, status=status.HTTP_404_NOT_FOUND)

            # Check if matchday template already exists for this pack
            try:
                existing_template = Template.objects.get(
                    graphic_pack=pack,
                    content_type='matchday'
                )
                logger.info(f"Matchday template already exists: {existing_template.id}")
                template = existing_template
            except Template.DoesNotExist:
                logger.info("Matchday template does not exist, creating new template")
                # Create a test matchday template for the user's selected pack
                template = Template.objects.create(
                    graphic_pack=pack,
                    content_type='matchday',
                    sport='football',
                    image_url='https://res.cloudinary.com/dxoxuyz0j/image/upload/v1755598719/Upcoming_Fixture_Home_tvlije.png',
                    template_config={
                        "date": {
                            "x": 100,
                            "y": 200,
                            "fontSize": 24,
                            "color": "#FFFFFF",
                            "fontFamily": "Arial"
                        },
                        "time": {
                            "x": 100,
                            "y": 250,
                            "fontSize": 24,
                            "color": "#FFFFFF",
                            "fontFamily": "Arial"
                        },
                        "venue": {
                            "x": 100,
                            "y": 300,
                            "fontSize": 20,
                            "color": "#FFFFFF",
                            "fontFamily": "Arial"
                        },
                        "opponent": {
                            "x": 100,
                            "y": 350,
                            "fontSize": 28,
                            "color": "#FFFFFF",
                            "fontFamily": "Arial"
                        },
                        "home_away": {
                            "x": 100,
                            "y": 150,
                            "fontSize": 32,
                            "color": "#FFFFFF",
                            "fontFamily": "Arial"
                        }
                    }
                )
                logger.info(f"Created test matchday template: {template.id}")

            return Response({
                "message": "Test data created successfully",
                "pack": {
                    "id": pack.id,
                    "name": pack.name,
                    "description": pack.description
                },
                "template": {
                    "id": template.id,
                    "content_type": template.content_type,
                    "has_config": bool(template.template_config)
                },
                "user_club": {
                    "name": club.name,
                    "selected_pack_id": pack.id
                }
            })

        except Exception as e:
            logger.error(f"Error creating test data: {str(e)}", exc_info=True)
            return Response({
                "error": f"Failed to create test data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


class SimpleTestView(APIView):
    """Simple test endpoint that doesn't use any models."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            logger.info("SimpleTestView called")
            return Response({
                "status": "success",
                "message": "Simple test endpoint working!",
                "user_email": request.user.email,
                "user_id": request.user.id,
                "timestamp": time.time()
            })
        except Exception as e:
            logger.error(f"SimpleTestView error: {str(e)}", exc_info=True)
            return Response({
                "status": "error",
                "message": f"Simple test failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TemplateDebugView(APIView):
    """Debug endpoint to directly check template data."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            logger.info("TemplateDebugView called")
            
            # Start with basic info
            basic_info = {
                "user_email": request.user.email,
                "user_id": request.user.id,
                "timestamp": time.time()
            }
            
            # Check migration status
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    # Check if template_config column exists
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'graphicpack_template' 
                        AND column_name = 'template_config'
                    """)
                    column_exists = cursor.fetchone() is not None
                    basic_info["template_config_column_exists"] = column_exists
                    
                    # Check migration status
                    cursor.execute("""
                        SELECT app, name, applied 
                        FROM django_migrations 
                        WHERE app = 'graphicpack' 
                        ORDER BY applied DESC
                    """)
                    migrations = cursor.fetchall()
                    basic_info["recent_migrations"] = migrations[:5]  # Last 5 migrations
                    
            except Exception as migration_error:
                logger.error(f"Migration check error: {str(migration_error)}")
                basic_info["migration_error"] = str(migration_error)
            
            # Try to get user's club
            try:
                club = Club.objects.get(user=request.user)
                pack_id = club.selected_pack.id if club.selected_pack else None
                basic_info["club_name"] = club.name
                basic_info["pack_id"] = pack_id
                logger.info(f"Found club: {club.name}, pack_id: {pack_id}")
            except Exception as club_error:
                logger.error(f"Club error: {str(club_error)}")
                basic_info["club_error"] = str(club_error)
                return Response(basic_info)
            
            if not pack_id:
                basic_info["error"] = "No pack selected"
                return Response(basic_info)
            
            # Try raw SQL first
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, content_type, sport, graphic_pack_id 
                        FROM graphicpack_template 
                        WHERE graphic_pack_id = %s
                    """, [pack_id])
                    raw_templates = cursor.fetchall()
                    logger.info(f"Raw SQL found {len(raw_templates)} templates: {raw_templates}")
                    basic_info["raw_sql_results"] = raw_templates
                    basic_info["raw_count"] = len(raw_templates)
            except Exception as sql_error:
                logger.error(f"SQL error: {str(sql_error)}")
                basic_info["sql_error"] = str(sql_error)
            
            # Try ORM
            try:
                pack = GraphicPack.objects.get(id=pack_id)
                orm_templates = Template.objects.filter(graphic_pack=pack)
                logger.info(f"ORM found {orm_templates.count()} templates")
                
                template_data = []
                for t in orm_templates:
                    template_data.append({
                        "id": t.id,
                        "content_type": t.content_type,
                        "sport": t.sport,
                        "graphic_pack_id": t.graphic_pack.id
                    })
                
                basic_info["orm_templates"] = template_data
                basic_info["orm_count"] = orm_templates.count()
                
                # Try to get matchday template specifically
                try:
                    matchday_template = Template.objects.get(
                        graphic_pack=pack,
                        content_type='matchday'
                    )
                    basic_info["matchday_template_found"] = True
                    basic_info["matchday_template_id"] = matchday_template.id
                except Template.DoesNotExist:
                    basic_info["matchday_template_found"] = False
                    basic_info["matchday_template_id"] = None
                    
            except Exception as orm_error:
                logger.error(f"ORM error: {str(orm_error)}")
                basic_info["orm_error"] = str(orm_error)
            
            return Response(basic_info)
            
        except Exception as e:
            logger.error(f"TemplateDebugView error: {str(e)}", exc_info=True)
            return Response({
                "error": f"Template debug failed: {str(e)}",
                "timestamp": time.time()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DiagnosticView(APIView):
    """Diagnostic endpoint to check current state for matchday post generation."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            logger.info(f"DiagnosticView called for user: {request.user.email}")
            
            # Start with basic user info
            user_info = {
                "email": request.user.email,
                "id": request.user.id
            }
            
            # Check user's club
            try:
                club = Club.objects.get(user=request.user)
                logger.info(f"Found club: {club.name} (ID: {club.id})")
                has_club = True
                club_name = club.name
                selected_pack_id = club.selected_pack.id if club.selected_pack else None
                selected_pack_name = club.selected_pack.name if club.selected_pack else None
            except Club.DoesNotExist:
                logger.warning(f"No club found for user: {request.user.email}")
                has_club = False
                club_name = None
                selected_pack_id = None
                selected_pack_name = None
            except Exception as club_error:
                logger.error(f"Error checking club: {str(club_error)}")
                has_club = False
                club_name = None
                selected_pack_id = None
                selected_pack_name = None

            # Check if selected pack exists
            pack_exists = False
            if selected_pack_id:
                try:
                    pack = GraphicPack.objects.get(id=selected_pack_id)
                    pack_exists = True
                    logger.info(f"Selected pack exists: {pack.name}")
                except GraphicPack.DoesNotExist:
                    logger.error(f"Selected pack ID {selected_pack_id} does not exist")
                    pack_exists = False
                except Exception as pack_error:
                    logger.error(f"Error checking pack: {str(pack_error)}")
                    pack_exists = False

            # Check for matchday template
            template_exists = False
            if pack_exists:
                try:
                    logger.info(f"Looking for matchday template with graphic_pack={pack.id} and content_type='matchday'")
                    
                    # Use raw SQL to check for matchday template since ORM has column issues
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT id, content_type, sport, graphic_pack_id 
                            FROM graphicpack_template 
                            WHERE graphic_pack_id = %s AND content_type = 'matchday'
                        """, [pack.id])
                        matchday_templates = cursor.fetchall()
                        logger.info(f"Raw SQL found {len(matchday_templates)} matchday templates for pack {pack.id}: {matchday_templates}")
                        
                        if matchday_templates:
                            template_exists = True
                            logger.info(f"Matchday template exists: {matchday_templates[0][0]}")
                        else:
                            logger.error(f"No matchday template found for pack {selected_pack_id}")
                            
                            # Check what content_types exist for this pack
                            cursor.execute("""
                                SELECT DISTINCT content_type 
                                FROM graphicpack_template 
                                WHERE graphic_pack_id = %s
                            """, [pack.id])
                            content_types = cursor.fetchall()
                            logger.error(f"Available content_types for pack {selected_pack_id}: {[ct[0] for ct in content_types]}")
                            
                except Exception as template_error:
                    logger.error(f"Error checking template: {str(template_error)}")
                    template_exists = False

            # Check user's matches
            matches_count = 0
            if has_club:
                try:
                    matches = Match.objects.filter(club=club)
                    matches_count = matches.count()
                    logger.info(f"User has {matches_count} matches")
                except Exception as matches_error:
                    logger.error(f"Error getting matches: {str(matches_error)}")
                    matches_count = 0

            return Response({
                "user": user_info,
                "club": {
                    "has_club": has_club,
                    "name": club_name,
                    "selected_pack_id": selected_pack_id,
                    "selected_pack_name": selected_pack_name
                },
                "pack": {
                    "exists": pack_exists,
                    "id": selected_pack_id
                },
                "template": {
                    "exists": template_exists,
                    "content_type": "matchday"
                },
                "matches": {
                    "count": matches_count
                },
                "status": "ready" if (has_club and pack_exists and template_exists and matches_count > 0) else "not_ready",
                "missing": []
            })

        except Exception as e:
            logger.error(f"Diagnostic error: {str(e)}", exc_info=True)
            return Response({
                "error": f"Diagnostic failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TextElementListView(ListAPIView):
    """List all text elements with filtering and pagination."""
    queryset = TextElement.objects.all()
    serializer_class = TextElementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = TextElement.objects.all()
        
        # Filter by content type
        content_type = self.request.query_params.get('content_type')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        # Filter by graphic pack
        graphic_pack = self.request.query_params.get('graphic_pack')
        if graphic_pack:
            queryset = queryset.filter(graphic_pack_id=graphic_pack)
        
        # Filter by element name
        element_name = self.request.query_params.get('element_name')
        if element_name:
            queryset = queryset.filter(element_name=element_name)
        
        # Search filter (searches across multiple fields)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(element_name__icontains=search) |
                Q(content_type__icontains=search) |
                Q(graphic_pack__name__icontains=search)
            )
        
        return queryset.order_by('graphic_pack__name', 'content_type', 'element_name')


class TextElementCreateView(APIView):
    """Create a new text element."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            serializer = TextElementSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating text element: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while creating the text element."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TextElementUpdateView(APIView):
    """Update an existing text element."""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, element_id):
        try:
            try:
                text_element = TextElement.objects.get(id=element_id)
                logger.info(f"Updating text element {element_id}")
                logger.info(f"Request data received: {request.data}")
                logger.info(f"Position anchor in request: {request.data.get('position_anchor', 'NOT PROVIDED')}")
                logger.info(f"Alignment in request: {request.data.get('alignment', 'NOT PROVIDED')}")
                logger.info(f"Position coordinates in request: x={request.data.get('position_x', 'NOT PROVIDED')}, y={request.data.get('position_y', 'NOT PROVIDED')}")
            except TextElement.DoesNotExist:
                return Response(
                    {"error": "Text element not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Log the incoming data for debugging
            logger.info(f"Updating text element {element_id} with data: {request.data}")
            
            # Handle position_anchor changes FIRST (before alignment changes)
            if 'position_anchor' in request.data:
                new_position_anchor = request.data['position_anchor']
                old_position_anchor = getattr(text_element, 'position_anchor', 'top')
                
                if new_position_anchor != old_position_anchor:
                    logger.info(f"Position anchor changed from {old_position_anchor} to {new_position_anchor}")
                    
                    # Update position based on current alignment and new position_anchor
                    current_alignment = request.data.get('alignment', text_element.alignment)
                    
                    if current_alignment == 'left':
                        if new_position_anchor == 'top':
                            request.data['position_x'] = text_element.top_left_x
                            request.data['position_y'] = text_element.top_left_y
                            logger.info(f"Updated position to top-left: ({text_element.top_left_x}, {text_element.top_left_y})")
                        elif new_position_anchor == 'center':
                            request.data['position_x'] = text_element.center_left_x
                            request.data['position_y'] = text_element.center_left_y
                            logger.info(f"Updated position to center-left: ({text_element.center_left_x}, {text_element.center_left_y})")
                        else:  # bottom
                            request.data['position_x'] = text_element.bottom_left_x
                            request.data['position_y'] = text_element.bottom_left_y
                            logger.info(f"Updated position to bottom-left: ({text_element.bottom_left_x}, {text_element.bottom_left_y})")
                    elif current_alignment == 'center':
                        if new_position_anchor == 'top':
                            request.data['position_x'] = text_element.top_center_x
                            request.data['position_y'] = text_element.top_center_y
                            logger.info(f"Updated position to top-center: ({text_element.top_center_x}, {text_element.top_center_y})")
                        elif new_position_anchor == 'center':
                            request.data['position_x'] = text_element.center_center_x
                            request.data['position_y'] = text_element.center_center_y
                            logger.info(f"Updated position to center-center: ({text_element.center_center_x}, {text_element.center_center_y})")
                        else:  # bottom
                            request.data['position_x'] = text_element.bottom_center_x
                            request.data['position_y'] = text_element.bottom_center_y
                            logger.info(f"Updated position to bottom-center: ({text_element.bottom_center_x}, {text_element.bottom_center_y})")
                    elif current_alignment == 'right':
                        if new_position_anchor == 'top':
                            request.data['position_x'] = text_element.top_right_x
                            request.data['position_y'] = text_element.top_right_y
                            logger.info(f"Updated position to top-right: ({text_element.top_right_x}, {text_element.top_right_y})")
                        elif new_position_anchor == 'center':
                            request.data['position_x'] = text_element.center_right_x
                            request.data['position_y'] = text_element.center_right_y
                            logger.info(f"Updated position to center-right: ({text_element.center_right_x}, {text_element.center_right_y})")
                        else:  # bottom
                            request.data['position_x'] = text_element.bottom_right_x
                            request.data['position_y'] = text_element.bottom_right_y
                            logger.info(f"Updated position to bottom-right: ({text_element.bottom_right_x}, {text_element.bottom_right_y})")
            
            # Check if alignment is being changed and update position accordingly
            if 'alignment' in request.data:
                new_alignment = request.data['alignment']
                old_alignment = text_element.alignment
                
                if new_alignment != old_alignment:
                    logger.info(f"Alignment changed from {old_alignment} to {new_alignment}")
                    
                    # Update position based on new alignment and position_anchor using stored anchor positions
                    # Use the position_anchor from request data if provided, otherwise use existing value
                    position_anchor = request.data.get('position_anchor', getattr(text_element, 'position_anchor', 'top'))
                    
                    if new_alignment == 'left':
                        if position_anchor == 'top':
                            request.data['position_x'] = text_element.top_left_x
                            request.data['position_y'] = text_element.top_left_y
                            logger.info(f"Updated position to top-left: ({text_element.top_left_x}, {text_element.top_left_y})")
                        elif position_anchor == 'center':
                            request.data['position_x'] = text_element.center_left_x
                            request.data['position_y'] = text_element.center_left_y
                            logger.info(f"Updated position to center-left: ({text_element.center_left_x}, {text_element.center_left_y})")
                        else:  # bottom
                            request.data['position_x'] = text_element.bottom_left_x
                            request.data['position_y'] = text_element.bottom_left_y
                            logger.info(f"Updated position to bottom-left: ({text_element.bottom_left_x}, {text_element.bottom_left_y})")
                    elif new_alignment == 'center':
                        if position_anchor == 'top':
                            request.data['position_x'] = text_element.top_center_x
                            request.data['position_y'] = text_element.top_center_y
                            logger.info(f"Updated position to top-center: ({text_element.top_center_x}, {text_element.top_center_y})")
                        elif position_anchor == 'center':
                            request.data['position_x'] = text_element.center_center_x
                            request.data['position_y'] = text_element.center_center_y
                            logger.info(f"Updated position to center-center: ({text_element.center_center_x}, {text_element.center_center_y})")
                        else:  # bottom
                            request.data['position_x'] = text_element.bottom_center_x
                            request.data['position_y'] = text_element.bottom_center_y
                            logger.info(f"Updated position to bottom-center: ({text_element.bottom_center_x}, {text_element.bottom_center_y})")
                    elif new_alignment == 'right':
                        if position_anchor == 'top':
                            request.data['position_x'] = text_element.top_right_x
                            request.data['position_y'] = text_element.top_right_y
                            logger.info(f"Updated position to top-right: ({text_element.top_right_x}, {text_element.top_right_y})")
                        elif position_anchor == 'center':
                            request.data['position_x'] = text_element.center_right_x
                            request.data['position_y'] = text_element.center_right_y
                            logger.info(f"Updated position to center-right: ({text_element.center_right_x}, {text_element.center_right_y})")
                        else:  # bottom
                            request.data['position_x'] = text_element.bottom_right_x
                            request.data['position_y'] = text_element.bottom_right_y
                            logger.info(f"Updated position to bottom-right: ({text_element.bottom_right_x}, {text_element.bottom_right_y})")
            
            serializer = TextElementSerializer(text_element, data=request.data, partial=True)
            if serializer.is_valid():
                updated_element = serializer.save()
                logger.info(f"Text element {element_id} updated successfully")
                logger.info(f"Final position_anchor: {updated_element.position_anchor}")
                logger.info(f"Final position: ({updated_element.position_x}, {updated_element.position_y})")
                logger.info(f"Final alignment: {updated_element.alignment}")
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                logger.error(f"Validation errors for text element {element_id}: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating text element: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while updating the text element."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TextElementDeleteView(APIView):
    """Delete a text element."""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, element_id):
        try:
            try:
                text_element = TextElement.objects.get(id=element_id)
            except TextElement.DoesNotExist:
                return Response(
                    {"error": "Text element not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            text_element.delete()
            return Response({"message": "Text element deleted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error deleting text element: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while deleting the text element."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BulkUpdateTextElementsView(APIView):
    """Bulk update multiple text elements."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            element_ids = request.data.get('element_ids', [])
            updates = request.data.get('updates', {})
            
            if not element_ids:
                return Response(
                    {"error": "No element IDs provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            if not updates:
                return Response(
                    {"error": "No updates provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Get the text elements
            text_elements = TextElement.objects.filter(id__in=element_ids)
            
            if not text_elements.exists():
                return Response(
                    {"error": "No text elements found with the provided IDs."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Update each element
            updated_count = 0
            for element in text_elements:
                for field, value in updates.items():
                    if hasattr(element, field):
                        setattr(element, field, value)
                element.save()
                updated_count += 1
            
            logger.info(f"Bulk updated {updated_count} text elements with updates: {updates}")
            
            return Response({
                "message": f"Successfully updated {updated_count} text elements.",
                "updated_count": updated_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in bulk update: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while updating the text elements."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GraphicPackDeleteView(APIView):
    """Delete a graphic pack and all its templates."""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, pack_id):
        try:
            try:
                graphic_pack = GraphicPack.objects.get(id=pack_id)
            except GraphicPack.DoesNotExist:
                return Response(
                    {"error": "Graphic pack not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Delete all templates associated with this pack
            templates = Template.objects.filter(graphic_pack=graphic_pack)
            templates_count = templates.count()
            templates.delete()
            
            # Delete the graphic pack
            graphic_pack.delete()
            
            return Response({
                "message": f"Graphic pack and {templates_count} templates deleted successfully."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error deleting graphic pack: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while deleting the graphic pack."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TemplateDeleteView(APIView):
    """Delete a template."""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, template_id):
        try:
            try:
                template = Template.objects.get(id=template_id)
            except Template.DoesNotExist:
                return Response(
                    {"error": "Template not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            template.delete()
            return Response({"message": "Template deleted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error deleting template: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while deleting the template."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GraphicPackCreateView(APIView):
    """Create a new graphic pack."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get data from request
            name = request.data.get('name')
            description = request.data.get('description', '')
            primary_color = request.data.get('primary_color', '#000000')
            sport = request.data.get('sport')
            tier = request.data.get('tier')
            assigned_club_id = request.data.get('assigned_club_id')
            preview_image_url = request.data.get('preview_image_url')
            is_active = request.data.get('is_active', True)
            
            if not name:
                return Response(
                    {"error": "Name is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Handle club assignment
            assigned_club = None
            if assigned_club_id:
                try:
                    from users.models import Club
                    assigned_club = Club.objects.get(id=assigned_club_id)
                except Club.DoesNotExist:
                    return Response(
                        {"error": "Club not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            
            # Create graphic pack
            graphic_pack = GraphicPack.objects.create(
                name=name,
                description=description,
                primary_color=primary_color,
                sport=sport,
                tier=tier,
                assigned_club=assigned_club,
                preview_image_url=preview_image_url,
                is_active=is_active
            )
            
            return Response({
                "message": "Graphic pack created successfully.",
                "graphic_pack": {
                    "id": graphic_pack.id,
                    "name": graphic_pack.name,
                    "description": graphic_pack.description,
                    "primary_color": graphic_pack.primary_color,
                    "sport": graphic_pack.sport,
                    "tier": graphic_pack.tier,
                    "preview_image_url": graphic_pack.preview_image_url,
                    "assigned_club_id": graphic_pack.assigned_club.id if graphic_pack.assigned_club else None,
                    "is_active": graphic_pack.is_active
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating graphic pack: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while creating the graphic pack."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GraphicPackUpdateView(APIView):
    """Update a graphic pack."""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, pack_id):
        try:
            try:
                graphic_pack = GraphicPack.objects.get(id=pack_id)
            except GraphicPack.DoesNotExist:
                return Response(
                    {"error": "Graphic pack not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Update fields
            if 'name' in request.data:
                graphic_pack.name = request.data['name']
            if 'description' in request.data:
                graphic_pack.description = request.data['description']
            if 'primary_color' in request.data:
                graphic_pack.primary_color = request.data['primary_color']
            if 'sport' in request.data:
                graphic_pack.sport = request.data['sport']
            if 'tier' in request.data:
                graphic_pack.tier = request.data['tier']
            if 'preview_image_url' in request.data:
                graphic_pack.preview_image_url = request.data['preview_image_url']
            if 'assigned_club_id' in request.data:
                club_id = request.data['assigned_club_id']
                if club_id:
                    try:
                        from users.models import Club
                        club = Club.objects.get(id=club_id)
                        graphic_pack.assigned_club = club
                    except Club.DoesNotExist:
                        return Response(
                            {"error": "Club not found."},
                            status=status.HTTP_404_NOT_FOUND,
                        )
                else:
                    graphic_pack.assigned_club = None
            if 'is_active' in request.data:
                graphic_pack.is_active = request.data['is_active']
            
            graphic_pack.save()
            
            return Response({
                "message": "Graphic pack updated successfully.",
                "graphic_pack": {
                    "id": graphic_pack.id,
                    "name": graphic_pack.name,
                    "description": graphic_pack.description,
                    "primary_color": graphic_pack.primary_color,
                    "sport": graphic_pack.sport,
                    "tier": graphic_pack.tier,
                    "preview_image_url": graphic_pack.preview_image_url,
                    "assigned_club_id": graphic_pack.assigned_club.id if graphic_pack.assigned_club else None,
                    "is_active": graphic_pack.is_active
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error updating graphic pack: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while updating the graphic pack."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TemplateCreateView(APIView):
    """Create a new template."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            file = request.FILES.get('file')
            content_type = request.data.get('content_type')
            graphic_pack_id = request.data.get('graphic_pack_id')
            
            if not file:
                return Response(
                    {"error": "File is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            if not content_type:
                return Response(
                    {"error": "Content type is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            if not graphic_pack_id:
                return Response(
                    {"error": "Graphic pack ID is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            try:
                graphic_pack = GraphicPack.objects.get(id=graphic_pack_id)
            except GraphicPack.DoesNotExist:
                return Response(
                    {"error": "Graphic pack not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Upload file to Cloudinary
            try:
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder=f"templates/{graphic_pack_id}",
                    resource_type="auto"
                )
            except Exception as upload_error:
                logger.error(f"Cloudinary upload failed: {str(upload_error)}")
                return Response(
                    {"error": "Failed to upload file."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            
            # Create template
            template = Template.objects.create(
                graphic_pack=graphic_pack,
                content_type=content_type,
                file_url=upload_result['secure_url'],
                image_url=upload_result['secure_url'],  # Save to image_url as well
                file_name=file.name,
                file_size=file.size
            )
            
            return Response({
                "message": "Template created successfully.",
                "template": {
                    "id": template.id,
                    "content_type": template.content_type,
                    "file_url": template.file_url,
                    "file_name": template.file_name
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}", exc_info=True)
            return Response(
                {"error": "An error occurred while creating the template."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TextElementByGraphicPackView(ListAPIView):
    """Get text elements for a specific graphic pack and content type."""
    serializer_class = TextElementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        graphic_pack_id = self.kwargs.get('graphic_pack_id')
        content_type = self.kwargs.get('content_type')
        
        queryset = TextElement.objects.filter(graphic_pack_id=graphic_pack_id)
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        return queryset


class AddOpponentLogoElementView(APIView):
    """Add opponent logo image element to user's selected graphic pack."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get user's club and selected pack
            club = Club.objects.get(user=request.user)
            if not club.selected_pack:
                return Response({
                    "error": "Club has no selected graphic pack"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            pack = club.selected_pack
            
            # Check if opponent logo element already exists
            existing_element = TextElement.objects.filter(
                graphic_pack=pack,
                content_type='matchday',
                element_name='opponent_logo'
            ).first()
            
            if existing_element:
                return Response({
                    "message": "Opponent logo element already exists",
                    "element_id": existing_element.id,
                    "element_details": {
                        "id": existing_element.id,
                        "element_type": existing_element.element_type,
                        "element_name": existing_element.element_name,
                        "position_x": existing_element.position_x,
                        "position_y": existing_element.position_y,
                        "image_width": existing_element.image_width,
                        "image_height": existing_element.image_height
                    }
                }, status=status.HTTP_200_OK)
            
            # Create the opponent logo image element
            element = TextElement.objects.create(
                graphic_pack=pack,
                content_type='matchday',
                element_name='opponent_logo',
                element_type='image',
                position_x=400,  # Center of image
                position_y=200,  # Adjust as needed
                image_width=150,
                image_height=150,
                maintain_aspect_ratio=True
            )
            
            logger.info(f"Created opponent logo element: {element.id} for pack {pack.name}")
            
            return Response({
                "message": "Opponent logo element created successfully",
                "element_id": element.id,
                "pack_name": pack.name,
                "element_details": {
                    "id": element.id,
                    "element_type": element.element_type,
                    "element_name": element.element_name,
                    "position_x": element.position_x,
                    "position_y": element.position_y,
                    "image_width": element.image_width,
                    "image_height": element.image_height
                }
            }, status=status.HTTP_201_CREATED)
            
        except Club.DoesNotExist:
            return Response({
                "error": "No club found for this user"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating opponent logo element: {str(e)}", exc_info=True)
            return Response({
                "error": f"Failed to create opponent logo element: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddClubLogoElementView(APIView):
    """Add club logo image element to user's selected graphic pack."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            logger.info("AddClubLogoElementView called")
            
            # Get user's club and selected pack
            club = Club.objects.get(user=request.user)
            pack = club.selected_pack
            
            if not pack:
                return Response({
                    "error": "No graphic pack selected for this club"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if club logo element already exists
            existing_element = TextElement.objects.filter(
                graphic_pack=pack,
                content_type='matchday',
                element_name='club_logo',
                element_type='image'
            ).first()
            
            if existing_element:
                return Response({
                    "message": "Club logo element already exists",
                    "element_id": existing_element.id,
                    "element_details": {
                        "id": existing_element.id,
                        "element_type": existing_element.element_type,
                        "element_name": existing_element.element_name,
                        "position_x": existing_element.position_x,
                        "position_y": existing_element.position_y,
                        "image_width": existing_element.image_width,
                        "image_height": existing_element.image_height
                    }
                }, status=status.HTTP_200_OK)
            
            # Create the club logo image element
            element = TextElement.objects.create(
                graphic_pack=pack,
                content_type='matchday',
                element_name='club_logo',
                element_type='image',
                position_x=200,  # Left side of image
                position_y=200,  # Adjust as needed
                image_width=150,
                image_height=150,
                maintain_aspect_ratio=True
            )
            
            logger.info(f"Created club logo element: {element.id} for pack {pack.name}")
            
            return Response({
                "message": "Club logo element created successfully",
                "element_id": element.id,
                "pack_name": pack.name,
                "element_details": {
                    "id": element.id,
                    "element_type": element.element_type,
                    "element_name": element.element_name,
                    "position_x": element.position_x,
                    "position_y": element.position_y,
                    "image_width": element.image_width,
                    "image_height": element.image_height
                }
            }, status=status.HTTP_201_CREATED)
            
        except Club.DoesNotExist:
            return Response({
                "error": "No club found for this user"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating club logo element: {str(e)}", exc_info=True)
            return Response({
                "error": f"Failed to create club logo element: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DebugOpponentLogoView(APIView):
    """Debug endpoint to check opponent logo setup."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get user's club and selected pack
            club = Club.objects.get(user=request.user)
            pack = club.selected_pack if club.selected_pack else None
            
            # Get all text elements for the pack
            text_elements = []
            if pack:
                text_elements = TextElement.objects.filter(graphic_pack=pack, content_type='matchday')
            
            # Get a sample match with opponent logo
            sample_match = None
            try:
                sample_match = Match.objects.filter(club=club, opponent_logo__isnull=False).exclude(opponent_logo='').first()
            except:
                pass
            
            return Response({
                "club": {
                    "name": club.name,
                    "selected_pack_id": pack.id if pack else None,
                    "selected_pack_name": pack.name if pack else None
                },
                "text_elements_count": text_elements.count(),
                "text_elements": [
                    {
                        "id": elem.id,
                        "element_name": elem.element_name,
                        "element_type": elem.element_type,
                        "position_x": elem.position_x,
                        "position_y": elem.position_y,
                        "image_width": elem.image_width if elem.element_type == 'image' else None,
                        "image_height": elem.image_height if elem.element_type == 'image' else None
                    } for elem in text_elements
                ],
                "opponent_logo_element_exists": text_elements.filter(element_name='opponent_logo', element_type='image').exists(),
                "sample_match": {
                    "id": sample_match.id if sample_match else None,
                    "opponent": sample_match.opponent if sample_match else None,
                    "opponent_logo": sample_match.opponent_logo if sample_match else None
                } if sample_match else None
            })
            
        except Exception as e:
            logger.error(f"Error in debug endpoint: {str(e)}", exc_info=True)
            return Response({
                "error": f"Debug failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TemplatesByPackView(APIView):
    """Get all templates for a specific graphic pack."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pack_id):
        try:
            logger.info(f"TemplatesByPackView called for pack_id: {pack_id}")
            logger.info(f"User: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
            logger.info(f"Request headers: {dict(request.headers)}")
            
            # Get the graphic pack
            try:
                pack = GraphicPack.objects.get(id=pack_id)
                logger.info(f"Found pack: {pack.name}")
            except GraphicPack.DoesNotExist:
                logger.error(f"Graphic pack not found: {pack_id}")
                return Response({
                    "error": "Graphic pack not found."
                }, status=status.HTTP_404_NOT_FOUND)

            # Get all templates for this pack
            try:
                templates = Template.objects.filter(graphic_pack=pack)
                logger.info(f"Found {templates.count()} templates for pack {pack.name}")
                
                templates_data = []
                for template in templates:
                    templates_data.append({
                        "id": template.id,
                        "content_type": template.content_type,
                        "image_url": template.image_url,
                        "sport": template.sport,
                        "template_config": template.template_config,
                        "has_config": bool(template.template_config)
                    })
                
                logger.info(f"Returning {len(templates_data)} templates")
                return Response({
                    "pack": {
                        "id": pack.id,
                        "name": pack.name,
                        "description": pack.description,
                    },
                    "templates": templates_data,
                    "templates_count": templates.count()
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error fetching templates: {str(e)}")
                return Response({
                    "error": f"Error fetching templates: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            logger.error(f"Error in TemplatesByPackView: {str(e)}", exc_info=True)
            return Response({
                "error": "An error occurred while retrieving templates."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddPlayerNameElementView(APIView):
    """Add player_name text element to user's selected graphic pack."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response({
                    "error": "No club found for this user"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get the club's selected graphic pack
            pack = club.selected_pack
            if not pack:
                return Response({
                    "error": "No graphic pack selected for this club"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if player_name element already exists
            existing_element = TextElement.objects.filter(
                graphic_pack=pack,
                content_type='goal',
                element_name='player_name'
            ).first()
            
            if existing_element:
                return Response({
                    "message": "Player name element already exists",
                    "element_id": existing_element.id,
                    "element_details": {
                        "id": existing_element.id,
                        "element_type": existing_element.element_type,
                        "element_name": existing_element.element_name,
                        "position_x": existing_element.position_x,
                        "position_y": existing_element.position_y,
                        "font_size": existing_element.font_size,
                        "font_family": existing_element.font_family,
                        "font_color": existing_element.font_color
                    }
                }, status=status.HTTP_200_OK)
            
            # Create the player_name text element
            element = TextElement.objects.create(
                graphic_pack=pack,
                content_type='goal',
                element_name='player_name',
                element_type='text',
                position_x=400,  # Center of image
                position_y=300,  # Adjust as needed
                font_size=24,
                font_family='Arial',
                font_color='#FFFFFF',
                alignment='center'
            )
            
            logger.info(f"Created player_name element: {element.id} for pack {pack.name}")
            
            return Response({
                "message": "Player name element created successfully",
                "element_id": element.id,
                "pack_name": pack.name,
                "element_details": {
                    "id": element.id,
                    "element_type": element.element_type,
                    "element_name": element.element_name,
                    "position_x": element.position_x,
                    "position_y": element.position_y,
                    "font_size": element.font_size,
                    "font_family": element.font_family,
                    "font_color": element.font_color
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating player_name element: {str(e)}", exc_info=True)
            return Response({
                "error": "An error occurred while creating the player name element."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddVenueElementView(APIView):
    """Add venue text element to user's selected graphic pack."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response({
                    "error": "No club found for this user"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get the club's selected graphic pack
            pack = club.selected_pack
            if not pack:
                return Response({
                    "error": "No graphic pack selected for this club"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if venue element already exists
            existing_element = TextElement.objects.filter(
                graphic_pack=pack,
                content_type='matchday',
                element_name='venue'
            ).first()
            
            if existing_element:
                return Response({
                    "message": "Venue element already exists",
                    "element_id": existing_element.id,
                    "element_details": {
                        "id": existing_element.id,
                        "element_type": existing_element.element_type,
                        "element_name": existing_element.element_name,
                        "position_x": existing_element.position_x,
                        "position_y": existing_element.position_y,
                        "font_size": existing_element.font_size,
                        "font_family": existing_element.font_family,
                        "font_color": existing_element.font_color
                    }
                }, status=status.HTTP_200_OK)
            
            # Create the venue text element
            element = TextElement.objects.create(
                graphic_pack=pack,
                content_type='matchday',
                element_name='venue',
                element_type='text',
                position_x=400,  # Center of image
                position_y=400,  # Adjust as needed
                font_size=20,
                font_family='Arial',
                font_color='#FFFFFF',
                alignment='center'
            )
            
            logger.info(f"Created venue element: {element.id} for pack {pack.name}")
            
            return Response({
                "message": "Venue element created successfully",
                "element_id": element.id,
                "pack_name": pack.name,
                "element_details": {
                    "id": element.id,
                    "element_type": element.element_type,
                    "element_name": element.element_name,
                    "position_x": element.position_x,
                    "position_y": element.position_y,
                    "font_size": element.font_size,
                    "font_family": element.font_family,
                    "font_color": element.font_color
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating venue element: {str(e)}", exc_info=True)
            return Response({
                "error": "An error occurred while creating the venue element."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddOpponentTextElementView(APIView):
    """Add opponent_text element to user's selected graphic pack."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response({
                    "error": "No club found for this user"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get the club's selected graphic pack
            pack = club.selected_pack
            if not pack:
                return Response({
                    "error": "No graphic pack selected for this club"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if opponent_text element already exists
            existing_element = TextElement.objects.filter(
                graphic_pack=pack,
                content_type='fixture',
                element_name='opponent_text'
            ).first()
            
            if existing_element:
                return Response({
                    "message": "Opponent text element already exists",
                    "element_id": existing_element.id,
                    "element_details": {
                        "id": existing_element.id,
                        "element_type": existing_element.element_type,
                        "element_name": existing_element.element_name,
                        "position_x": existing_element.position_x,
                        "position_y": existing_element.position_y,
                        "font_size": existing_element.font_size,
                        "font_family": existing_element.font_family,
                        "font_color": existing_element.font_color
                    }
                }, status=status.HTTP_200_OK)
            
            # Create the opponent_text element
            element = TextElement.objects.create(
                graphic_pack=pack,
                content_type='fixture',
                element_name='opponent_text',
                element_type='text',
                position_x=400,  # Center of image
                position_y=200,  # Adjust as needed
                font_size=24,
                font_family='Arial',
                font_color='#FFFFFF',
                alignment='center'
            )
            
            logger.info(f"Created opponent_text element: {element.id} for pack {pack.name}")
            
            return Response({
                "message": "Opponent text element created successfully",
                "element_id": element.id,
                "pack_name": pack.name,
                "element_details": {
                    "id": element.id,
                    "element_type": element.element_type,
                    "element_name": element.element_name,
                    "position_x": element.position_x,
                    "position_y": element.position_y,
                    "font_size": element.font_size,
                    "font_family": element.font_family,
                    "font_color": element.font_color
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating opponent_text element: {str(e)}", exc_info=True)
            return Response({
                "error": "An error occurred while creating the opponent text element."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddClubLogoAltElementView(APIView):
    """Add club_logo_alt element to user's selected graphic pack."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response({
                    "error": "No club found for this user"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get the club's selected graphic pack
            pack = club.selected_pack
            if not pack:
                return Response({
                    "error": "No graphic pack selected for this club"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if club_logo_alt element already exists
            existing_element = TextElement.objects.filter(
                graphic_pack=pack,
                content_type='fixture',
                element_name='club_logo_alt'
            ).first()
            
            if existing_element:
                return Response({
                    "message": "Club logo alt element already exists",
                    "element_id": existing_element.id,
                    "element_details": {
                        "id": existing_element.id,
                        "element_type": existing_element.element_type,
                        "element_name": existing_element.element_name,
                        "position_x": existing_element.position_x,
                        "position_y": existing_element.position_y,
                        "font_size": existing_element.font_size,
                        "font_family": existing_element.font_family,
                        "font_color": existing_element.font_color
                    }
                }, status=status.HTTP_200_OK)
            
            # Create the club_logo_alt element
            element = TextElement.objects.create(
                graphic_pack=pack,
                content_type='fixture',
                element_name='club_logo_alt',
                element_type='text',
                position_x=200,  # Left side of image
                position_y=200,  # Adjust as needed
                font_size=24,
                font_family='Arial',
                font_color='#FFFFFF',
                alignment='center'
            )
            
            logger.info(f"Created club_logo_alt element: {element.id} for pack {pack.name}")
            
            return Response({
                "message": "Club logo alt element created successfully",
                "element_id": element.id,
                "pack_name": pack.name,
                "element_details": {
                    "id": element.id,
                    "element_type": element.element_type,
                    "element_name": element.element_name,
                    "position_x": element.position_x,
                    "position_y": element.position_y,
                    "font_size": element.font_size,
                    "font_family": element.font_family,
                    "font_color": element.font_color
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating club_logo_alt element: {str(e)}", exc_info=True)
            return Response({
                "error": "An error occurred while creating the club logo alt element."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Media Management Views

class MediaItemListView(ListAPIView):
    """List all media items for the authenticated user's club."""
    serializer_class = MediaItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter media items by club and optional filters."""
        try:
            club = Club.objects.get(user=self.request.user)
            queryset = MediaItem.objects.filter(club=club, is_active=True)
            
            # Filter by media type
            media_type = self.request.query_params.get('media_type')
            if media_type:
                queryset = queryset.filter(media_type=media_type)
            
            # Filter by category
            category = self.request.query_params.get('category')
            if category:
                queryset = queryset.filter(category=category)
            
            # Search by title or description
            search = self.request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) | 
                    Q(description__icontains=search) |
                    Q(tags__icontains=search)
                )
            
            return queryset.order_by('-created_at')
            
        except Club.DoesNotExist:
            return MediaItem.objects.none()


class MediaItemUploadView(APIView):
    """Upload a new media item."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Upload a media file to Cloudinary and create a MediaItem record."""
        try:
            # Get user's club
            try:
                club = Club.objects.get(user=request.user)
            except Club.DoesNotExist:
                return Response({
                    "error": "No club found for this user"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate required fields
            file = request.FILES.get('file')
            if not file:
                return Response({
                    "error": "No file provided"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            media_type = request.data.get('media_type')
            if not media_type:
                return Response({
                    "error": "media_type is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file size (max 50MB)
            max_size = 50 * 1024 * 1024  # 50MB
            if file.size > max_size:
                return Response({
                    "error": "File size cannot exceed 50MB"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file type
            allowed_types = [
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
                'image/svg+xml', 'application/pdf'
            ]
            if file.content_type not in allowed_types:
                return Response({
                    "error": f"File type not supported. Allowed types: {', '.join(allowed_types)}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Determine category based on media type
            category_mapping = {
                'club_logo': 'logos',
                'opponent_logo': 'logos',
                'player_photo': 'players',
                'template': 'templates',
                'background': 'backgrounds',
                'banner': 'banners',
                'other': 'other'
            }
            category = category_mapping.get(media_type, 'other')
            
            # Upload to Cloudinary
            try:
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder=f"media/{club.id}/{category}",
                    resource_type="auto",
                    quality="auto:best",
                    format="auto"
                )
            except Exception as upload_error:
                logger.error(f"Cloudinary upload failed: {str(upload_error)}")
                return Response({
                    "error": "Failed to upload file to Cloudinary"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Get image dimensions if it's an image
            width = None
            height = None
            if file.content_type.startswith('image/'):
                try:
                    from PIL import Image
                    img = Image.open(file)
                    width, height = img.size
                except Exception as e:
                    logger.warning(f"Could not get image dimensions: {str(e)}")
            
            # Create MediaItem record
            media_item = MediaItem.objects.create(
                club=club,
                title=request.data.get('title', file.name),
                description=request.data.get('description', ''),
                media_type=media_type,
                category=category,
                file_url=upload_result['secure_url'],
                file_name=file.name,
                file_size=file.size,
                file_type=file.content_type,
                width=width,
                height=height,
                cloudinary_public_id=upload_result['public_id'],
                cloudinary_folder=upload_result.get('folder', ''),
                tags=request.data.get('tags', [])
            )
            
            # If this is a club logo, update the club's logo field
            if media_type == 'club_logo':
                club.logo = upload_result['secure_url']
                club.save()
                logger.info(f"Updated club logo for {club.name}")
            
            # If this is an opponent logo, we might want to update a match's opponent_logo
            # This would need to be handled based on the specific match context
            
            serializer = MediaItemSerializer(media_item)
            return Response({
                "message": "Media item uploaded successfully",
                "media_item": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error uploading media item: {str(e)}", exc_info=True)
            return Response({
                "error": "An error occurred while uploading the media item"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MediaItemDetailView(APIView):
    """Get, update, or delete a specific media item."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, media_id):
        """Get a specific media item."""
        try:
            club = Club.objects.get(user=request.user)
            media_item = MediaItem.objects.get(id=media_id, club=club)
            serializer = MediaItemSerializer(media_item)
            return Response(serializer.data)
        except Club.DoesNotExist:
            return Response({
                "error": "No club found for this user"
            }, status=status.HTTP_404_NOT_FOUND)
        except MediaItem.DoesNotExist:
            return Response({
                "error": "Media item not found"
            }, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, media_id):
        """Update a media item."""
        try:
            club = Club.objects.get(user=request.user)
            media_item = MediaItem.objects.get(id=media_id, club=club)
            
            # Update allowed fields
            allowed_fields = ['title', 'description', 'tags', 'is_active']
            for field in allowed_fields:
                if field in request.data:
                    setattr(media_item, field, request.data[field])
            
            media_item.save()
            serializer = MediaItemSerializer(media_item)
            return Response({
                "message": "Media item updated successfully",
                "media_item": serializer.data
            })
            
        except Club.DoesNotExist:
            return Response({
                "error": "No club found for this user"
            }, status=status.HTTP_404_NOT_FOUND)
        except MediaItem.DoesNotExist:
            return Response({
                "error": "Media item not found"
            }, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, media_id):
        """Delete a media item."""
        try:
            club = Club.objects.get(user=request.user)
            media_item = MediaItem.objects.get(id=media_id, club=club)
            
            # Delete from Cloudinary
            if media_item.cloudinary_public_id:
                try:
                    cloudinary.uploader.destroy(media_item.cloudinary_public_id)
                except Exception as e:
                    logger.warning(f"Failed to delete from Cloudinary: {str(e)}")
            
            # Delete from database
            media_item.delete()
            
            return Response({
                "message": "Media item deleted successfully"
            })
            
        except Club.DoesNotExist:
            return Response({
                "error": "No club found for this user"
            }, status=status.HTTP_404_NOT_FOUND)
        except MediaItem.DoesNotExist:
            return Response({
                "error": "Media item not found"
            }, status=status.HTTP_404_NOT_FOUND)


class MediaItemStatsView(APIView):
    """Get statistics about media items."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get media statistics for the user's club."""
        try:
            club = Club.objects.get(user=request.user)
            media_items = MediaItem.objects.filter(club=club, is_active=True)
            
            # Count by media type
            media_type_counts = {}
            for media_type, _ in MediaItem.MEDIA_TYPES:
                count = media_items.filter(media_type=media_type).count()
                if count > 0:
                    media_type_counts[media_type] = count
            
            # Count by category
            category_counts = {}
            for category, _ in MediaItem.CATEGORIES:
                count = media_items.filter(category=category).count()
                if count > 0:
                    category_counts[category] = count
            
            # Total file size
            total_size = sum(item.file_size for item in media_items)
            total_size_mb = round(total_size / (1024 * 1024), 2)
            
            return Response({
                "total_items": media_items.count(),
                "total_size_mb": total_size_mb,
                "media_type_counts": media_type_counts,
                "category_counts": category_counts,
                "club_name": club.name
            })
            
        except Club.DoesNotExist:
            return Response({
                "error": "No club found for this user"
            }, status=status.HTTP_404_NOT_FOUND)