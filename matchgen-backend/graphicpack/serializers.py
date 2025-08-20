from rest_framework import serializers
import logging

from .models import GraphicPack, UserSelection, Template, TemplateElement, StringElement, ImageElement

logger = logging.getLogger(__name__)


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

    def to_representation(self, instance):
        """Override to handle missing fields gracefully."""
        try:
            data = super().to_representation(instance)
            logger.info(f"Successfully serialized GraphicPack: {instance.id}")
            return data
        except Exception as e:
            logger.error(f"Error serializing GraphicPack {instance.id}: {str(e)}")
            # Return basic data without templates if there's an error
            return {
                'id': instance.id,
                'name': instance.name,
                'description': instance.description,
                'preview_image_url': getattr(instance, 'preview_image_url', None),
                'templates': []
            }


class SimpleGraphicPackSerializer(serializers.ModelSerializer):
    """Simple serializer for basic graphic pack data without templates."""
    
    class Meta:
        model = GraphicPack
        fields = ['id', 'name', 'description', 'preview_image_url']
