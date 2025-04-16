from django.shortcuts import get_object_or_404, render
from rest_framework import generics, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import GraphicPack, UserSelection, TextElement
from users.models import Club
from .serializers import GraphicPackSerializer
from rest_framework.parsers import JSONParser, MultiPartParser
from django.utils import timezone
from rest_framework.views import APIView
import csv, io
from django.http import JsonResponse
from content.models import Match
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests
import cloudinary.uploader
from .utils import get_static_font_path


class GraphicPackListView(ListAPIView):
    queryset = GraphicPack.objects.all()
    serializer_class = GraphicPackSerializer

# class SelectGraphicPackView(APIView):
#     def post(self, request):
#         pack_id = request.data.get("pack_id")
#         pack = get_object_or_404(GraphicPack, id=pack_id)
#         UserSelection.objects.update_or_create(user=request.user, defaults={"selected_pack": pack})
#         return Response({"status": "selected", "pack": pack_id})
    
class SelectGraphicPackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pack_id = request.data.get("pack_id")
        if not pack_id:
            return Response({"error": "pack_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        pack = get_object_or_404(GraphicPack, id=pack_id)

        try:
            club = Club.objects.get(user=request.user)
        except Club.DoesNotExist:
            return Response({"error": "Club not found for this user"}, status=status.HTTP_404_NOT_FOUND)

        club.selected_pack = pack
        club.save()

        return Response({"status": "selected", "pack": pack_id}, status=status.HTTP_200_OK)
    




def generate_matchday(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    club = match.club
    selected_pack = club.selected_pack

    if not selected_pack:
        return JsonResponse({"error": "Club has no selected graphic pack."}, status=400)

    try:
        template = selected_pack.templates.get(content_type="matchday")
    except:
        return JsonResponse({"error": "Matchday template not found in selected pack."}, status=404)

    # Load base image
    response = requests.get(template.background_image.url)
    base_image = Image.open(BytesIO(response.content)).convert("RGBA")
    draw = ImageDraw.Draw(base_image)
    image_width, image_height = base_image.size

    # Fetch dynamic text elements
    text_elements = TextElement.objects.filter(template=template)

    # Mapping placeholders to actual match data
    content_map = {
        "opponent": match.opponent or "Opponent",
        "date": match.date.strftime("%A, %b %d"),
        "time": match.time_start or match.date.strftime("%I:%M %p"),
        "venue": match.venue or "Venue",
    }

    for element in text_elements:
        text = content_map.get(element.placeholder, f"[{element.placeholder}]")
        
        font_path = get_static_font_path(
            font_family=element.primary_font_family
            # bold=getattr(element, "bold", False),
            # italic=getattr(element, "italic", False),
        )

        try:
            font = ImageFont.truetype(font_path, element.primary_font_size)
        except Exception as e:
            print(f"Font load failed for {font_path}: {e}")
            font = ImageFont.load_default()

        # Calculate position
        x = int(element.primary_position_x)
        y = int(element.primary_position_y)

        # Text alignment
        text_size = draw.textsize(text, font=font)
        if element.alignment == "center":
            x -= text_size[0] // 2
        elif element.alignment == "right":
            x -= text_size[0]

        draw.text((x, y), text, font=font, fill=element.secondary_text_color)

    # Save & upload
    buffer = BytesIO()
    base_image.save(buffer, format="PNG")
    buffer.seek(0)

    upload_result = cloudinary.uploader.upload(
        buffer,
        folder=f"matchday_posts/club_{club.id}/",
        public_id=f"match_{match.id}",
        overwrite=True,
        resource_type="image"
    )

    match.matchday_post_url = upload_result['secure_url']
    match.save()

    return JsonResponse({"url": upload_result['secure_url']})
