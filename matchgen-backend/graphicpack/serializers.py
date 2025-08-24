from rest_framework import serializers
import logging

from .models import GraphicPack, UserSelection, Template, TextElement

logger = logging.getLogger(__name__)


class TemplateSerializer(serializers.ModelSerializer):
    """Serializer for Template model with JSON-based configuration."""
    
    class Meta:
        model = Template
        fields = '__all__'

    def to_representation(self, instance):
        """Override to handle missing fields gracefully."""
        try:
            data = super().to_representation(instance)
            return data
        except Exception as e:
            logger.error(f"Error serializing Template {instance.id}: {str(e)}")
            # Return basic data if there's an error
            return {
                'id': instance.id,
                'graphic_pack': instance.graphic_pack.id,
                'content_type': instance.content_type,
                'image_url': instance.image_url,
                'sport': instance.sport,
                'template_config': getattr(instance, 'template_config', {})
            }


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


class TextElementSerializer(serializers.ModelSerializer):
    """Serializer for TextElement model."""
    graphic_pack_name = serializers.CharField(source='graphic_pack.name', read_only=True)
    
    class Meta:
        model = TextElement
        fields = [
            'id', 'graphic_pack', 'graphic_pack_name', 'content_type', 'element_name',
            'element_type', 'position_x', 'position_y', 'font_size', 'font_family', 'font_color',
            'alignment', 'font_weight', 'image_width', 'image_height', 'maintain_aspect_ratio',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_font_color(self, value):
        """Validate hex color format."""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Color must be a valid hex color (e.g., #FFFFFF)")
        return value
