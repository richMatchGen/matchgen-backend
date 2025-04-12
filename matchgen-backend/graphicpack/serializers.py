from rest_framework import serializers
from .models import GraphicPack, UserSelection

class GraphicPackSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraphicPack
        fields = [
            "name","description", "preview_image", "zip_file"
        ]


