from django.shortcuts import get_object_or_404, render
from rest_framework import generics, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import GraphicPack, UserSelection
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

    # Load base image from URL
    response = requests.get(template.image_url)
    base_image = Image.open(BytesIO(response.content)).convert("RGBA")
    draw = ImageDraw.Draw(base_image)

    # Load font
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 164)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw match info
    draw.text((520, 80), match.opponent or "Opponent", font=font_large, fill="white")
    draw.text((633, 740), match.date.strftime("%A, %b %d"), font=font_large, fill="black")
    draw.text((520, 210), match.time_start or match.date.strftime("%I:%M %p"), font=font_small, fill="white")
    draw.text((520, 260), match.venue or "Venue", font=font_small, fill="white")

    # Save to in-memory file
    buffer = BytesIO()
    base_image.save(buffer, format="PNG")
    buffer.seek(0)

    # Upload to Cloudinary
    upload_result = cloudinary.uploader.upload(
        buffer,
        folder=f"matchday_posts/club_{club.id}/",
        public_id=f"match_{match.id}",
        overwrite=True,
        resource_type="image"
    )

    # Save URL to model (optional)
    match.matchday_post_url = upload_result['secure_url']
    match.save()

    return JsonResponse({"url": upload_result['secure_url']})
