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
    assigned_club_name = serializers.CharField(source='assigned_club.name', read_only=True)
    
    class Meta:
        model = GraphicPack
        fields = [
            'id', 'name', 'description', 'preview_image_url', 'zip_file_url',
            'primary_color', 'tier', 'assigned_club', 'assigned_club_name', 'is_active',
            'sport', 'created_at', 'updated_at', 'templates'
        ]
        read_only_fields = ['created_at', 'updated_at']

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
                'primary_color': getattr(instance, 'primary_color', '#000000'),
                'tier': getattr(instance, 'tier', None),
                'assigned_club': getattr(instance, 'assigned_club', None),
                'is_active': getattr(instance, 'is_active', True),
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
            'element_type', 'position_x', 'position_y', 'top_left_x', 'top_left_y', 'top_right_x', 'top_right_y', 'home_position_x', 'home_position_y',
            'away_position_x', 'away_position_y', 'font_size', 'font_family', 'font_color',
            'alignment', 'text_alignment', 'anchor_point', 'font_weight', 'image_width', 'image_height', 'maintain_aspect_ratio',
            'image_color_filter', 'image_color_tint', 'image_brightness', 'image_contrast', 'image_saturation',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_font_color(self, value):
        """Validate hex color format."""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Color must be a valid hex color (e.g., #FFFFFF)")
        return value
    
    def validate_image_color_tint(self, value):
        """Validate hex color format for image tint."""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Color must be a valid hex color (e.g., #FFFFFF)")
        return value
