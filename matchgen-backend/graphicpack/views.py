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
import os
from .utils import get_font
import logging


class GraphicPackListView(ListAPIView):
    queryset = GraphicPack.objects.all()
    serializer_class = GraphicPackSerializer

  
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

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test_line = f"{line} {word}".strip()
        if draw.textlength(test_line, font=font) <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def get_element_content(match, club, key):
    return {
        "club_name": club.name,
        "opponent": match.opponent or "Opponent",
        "match_date": match.date.strftime("%d.%m.%Y"),
        "kickoff_time": match.time_start or match.date.strftime("%I:%M %p"),
        "venue": match.venue or "Venue",
        # Add more keys here as needed
    }.get(key)


logger = logging.getLogger(__name__)

def generate_matchday(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    club = match.club
    selected_pack = club.selected_pack
    logger.debug(f"Generating matchday for match ID: {match_id}")

    if not selected_pack:
        return JsonResponse({"error": "Club has no selected graphic pack."}, status=400)

    template = selected_pack.templates.filter(content_type="matchday").first()
    if not template:
        return JsonResponse({"error": "No matchday template found in selected pack."}, status=404)

    # Load base image
    response = requests.get(template.image_url)
    base_image = Image.open(BytesIO(response.content)).convert("RGBA")
    draw = ImageDraw.Draw(base_image)

    # Render text elements
    for element in template.string_elements.all():
        content = get_element_content(match, club, element.content_key)
        if not content:
            continue

        font = get_font(element.font_family, element.font_size)
        x, y = element.x, element.y
        color = element.color or "#FFFFFF"

        if element.max_width:
            lines = wrap_text(draw, str(content), font, element.max_width)
            line_height = font.getsize("Ay")[1]
            for i, line in enumerate(lines):
                line_x = x
                if element.alignment == "center":
                    line_x = x - draw.textlength(line, font=font) / 2
                elif element.alignment == "right":
                    line_x = x - draw.textlength(line, font=font)

                draw.text((line_x, y + i * line_height), line, font=font, fill=color)
        else:
            if element.alignment == "center":
                x -= draw.textlength(str(content), font=font) / 2
            elif element.alignment == "right":
                x -= draw.textlength(str(content), font=font)

            draw.text((x, y), str(content), font=font, fill=color)

    # Save image to buffer
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

    match.matchday_post_url = upload_result['secure_url']
    match.save()

    return JsonResponse({"url": upload_result['secure_url']})


