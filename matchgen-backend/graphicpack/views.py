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

from .models import GraphicPack, Template, TextElement
from .serializers import GraphicPackSerializer, TextElementSerializer

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
        
        # Render each text element
        for text_element in text_elements:
            # Get the value for this element
            value = fixture_data.get(text_element.element_name, "")
            if not value:
                logger.info(f"Skipping {text_element.element_name} - no value available")
                continue
                
            logger.info(f"Rendering: {text_element.element_name} = '{value}'")

            try:
                # Get font settings directly from TextElement
                font_size = text_element.font_size
                font_family = text_element.font_family
                font_color = text_element.font_color
                position_x = text_element.position_x
                position_y = text_element.position_y
                alignment = text_element.alignment
                
                logger.info(f"Font settings: size={font_size}, family={font_family}, color={font_color}, pos=({position_x},{position_y})")
                
                # Load font with the specified size
                try:
                    # Try to load a scalable font with the specified size
                    import os
                    from django.conf import settings
                    
                    # Get the static fonts directory
                    static_fonts_dir = os.path.join(settings.BASE_DIR, 'static', 'fonts')
                    
                    font_paths = [
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
                    ]
                    
                    font = None
                    for font_path in font_paths:
                        try:
                            font = ImageFont.truetype(font_path, font_size)
                            logger.info(f"✅ SUCCESS: Loaded font from {font_path} with size {font_size}")
                            break
                        except Exception as e:
                            logger.debug(f"Failed to load font from {font_path}: {e}")
                            continue
                    
                    # If no scalable font found, use default with warning
                    if font is None:
                        logger.warning(f"❌ WARNING: No TrueType font could be loaded. Falling back to default font, which ignores font_size={font_size}")
                        logger.warning(f"❌ Text will appear tiny regardless of font_size setting")
                        font = ImageFont.load_default()
                        
                        # Apply text scaling to simulate larger font size
                        if font_size > 24:
                            logger.info(f"🔧 Applying text scaling to simulate font size {font_size}")
                            # We'll handle this in the rendering section
                        
                except Exception as e:
                    logger.warning(f"❌ Font loading error, using default font: {e}")
                    font = ImageFont.load_default()
                
                # Get color
                color = font_color
                
                # Calculate text position based on alignment
                bbox = draw.textbbox((0, 0), value, font=font)
                text_width = bbox[2] - bbox[0]
                
                if alignment == 'center':
                    x = position_x - (text_width // 2)
                elif alignment == 'right':
                    x = position_x - text_width
                else:  # left
                    x = position_x
                
                # Draw the text
                draw.text((x, position_y), value, font=font, fill=color)
                
                # If using default font and font size is large, apply scaling effect
                if isinstance(font, type(ImageFont.load_default())) and font_size > 24:
                    logger.info(f"🔧 Applying text scaling effect for size {font_size}")
                    
                    # Calculate scale factor
                    scale_factor = max(2, font_size // 12)
                    
                    # Draw multiple layers to create a "larger" text effect
                    for offset in range(1, scale_factor):
                        for dx in [-offset, 0, offset]:
                            for dy in [-offset, 0, offset]:
                                if dx != 0 or dy != 0:  # Don't redraw at center
                                    draw.text((x + dx, position_y + dy), value, font=font, fill=color)
                    
                    logger.info(f"✅ Applied text scaling with {scale_factor} layers")
                
                # Debug: Draw a red rectangle around the text to show its actual size
                bbox = draw.textbbox((x, position_y), value, font=font)
                draw.rectangle(bbox, outline="red", width=2)
                
                logger.info(f"Rendered '{value}' at ({x}, {position_y}) with size {font_size}")
                logger.info(f"Text bounding box: {bbox} (width: {bbox[2]-bbox[0]}, height: {bbox[3]-bbox[1]})")
                
            except Exception as e:
                logger.error(f"Error rendering text element {text_element.element_name}: {str(e)}")
                continue

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
    """List all text elements."""
    queryset = TextElement.objects.all()
    serializer_class = TextElementSerializer
    permission_classes = [IsAuthenticated]


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
            except TextElement.DoesNotExist:
                return Response(
                    {"error": "Text element not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            serializer = TextElementSerializer(text_element, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
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