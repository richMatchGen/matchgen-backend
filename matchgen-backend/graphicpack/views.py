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