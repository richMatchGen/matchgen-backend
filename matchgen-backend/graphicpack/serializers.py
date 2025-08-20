from rest_framework import serializers

from .models import GraphicPack, UserSelection, Template, TemplateElement, StringElement, ImageElement


class StringElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StringElement
        fields = '__all__'


class ImageElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageElement
        fields = '__all__'


class TemplateElementSerializer(serializers.ModelSerializer):
    string_elements = StringElementSerializer(many=True, read_only=True)
    image_elements = ImageElementSerializer(many=True, read_only=True)
    
    class Meta:
        model = TemplateElement
        fields = '__all__'


class TemplateSerializer(serializers.ModelSerializer):
    elements = TemplateElementSerializer(many=True, read_only=True)
    
    class Meta:
        model = Template
        fields = '__all__'


class GraphicPackSerializer(serializers.ModelSerializer):
    templates = TemplateSerializer(many=True, read_only=True)
    
    class Meta:
        model = GraphicPack
        fields = '__all__'
