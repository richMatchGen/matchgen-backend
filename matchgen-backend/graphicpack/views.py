import csv
import io
import logging
import os
from io import BytesIO

import cloudinary.uploader
import requests
from content.models import Match
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont
from rest_framework import generics, status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import Club

from .models import (GraphicPack, ImageElement, StringElement, Template,
                     TextElement, UserSelection)
from .serializers import GraphicPackSerializer
from .utils import get_font


class GraphicPackListView(ListAPIView):
    queryset = GraphicPack.objects.all()
    serializer_class = GraphicPackSerializer


class SelectGraphicPackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
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
                {"error": "Club not found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )

        club.selected_pack = pack
        club.save()

        return Response(
            {"status": "selected", "pack": pack_id}, status=status.HTTP_200_OK
        )


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


def generate_matchday(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    club = match.club
    selected_pack = club.selected_pack

    if not selected_pack:
        return JsonResponse({"error": "Club has no selected graphic pack."}, status=400)

    try:
        template = selected_pack.templates.get(content_type="matchday")
    except Template.DoesNotExist:
        return JsonResponse(
            {"error": "Matchday template not found in selected pack."}, status=404
        )

    # Load base image from URL
    response = requests.get(template.image_url)
    base_image = Image.open(BytesIO(response.content)).convert("RGBA")
    draw = ImageDraw.Draw(base_image)

    # Content mapping
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

    # Render text elements
    for element in template.elements.filter(type="text"):
        for string in element.string_elements.all():
            value = content.get(string.content_key, "")
            if not value:
                continue

            font = get_font(string.font_family, string.font_size)

            draw.text((element.x, element.y), value, font=font, fill=string.color)

    # Render image elements
    for element in template.elements.filter(type="image"):
        for image in element.image_elements.all():
            image_url = content.get(image.content_key)
            if not image_url:
                continue
            try:
                img_response = requests.get(image_url)
                img = Image.open(BytesIO(img_response.content)).convert("RGBA")

                if image.maintain_aspect_ratio:
                    img.thumbnail((element.width, element.height))
                else:
                    img = img.resize((int(element.width), int(element.height)))

                base_image.paste(img, (int(element.x), int(element.y)), img)
            except Exception as e:
                print(f"Error loading image: {e}")
                continue

    # Save to buffer
    buffer = BytesIO()
    base_image.save(buffer, format="PNG")
    buffer.seek(0)

    # Upload to Cloudinary
    upload_result = cloudinary.uploader.upload(
        buffer,
        folder=f"matchday_posts/club_{club.id}/",
        public_id=f"match_{match.id}",
        overwrite=True,
        resource_type="image",
    )

    match.matchday_post_url = upload_result["secure_url"]
    match.save()

    return JsonResponse({"url": upload_result["secure_url"]})
