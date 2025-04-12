from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import GraphicPack, UserSelection
from users.models import Club
from .serializers import MatchSerializer,PlayerSerializer
from rest_framework.parsers import JSONParser, MultiPartParser
from django.utils import timezone
from rest_framework.views import APIView
import csv, io

# Create your views here.
class GraphicPackListView(generics.ListAPIView):
    queryset = GraphicPack.objects.all()
    serializer_class = GraphicPackSerializer

class SelectGraphicPackView(APIView):
    def post(self, request):
        pack_id = request.data.get("pack_id")
        pack = get_object_or_404(GraphicPack, id=pack_id)
        UserSelection.objects.update_or_create(user=request.user, defaults={"selected_pack": pack})
        return Response({"status": "selected", "pack": pack_id})