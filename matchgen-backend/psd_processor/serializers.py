from rest_framework import serializers
from .models import PSDDocument, PSDLayer


class PSDLayerSerializer(serializers.ModelSerializer):
    """Serializer for PSD layer information."""
    bounding_box = serializers.ReadOnlyField()
    
    class Meta:
        model = PSDLayer
        fields = ['id', 'name', 'x', 'y', 'width', 'height', 'visible', 'opacity', 'layer_type', 'bounding_box']


class PSDDocumentSerializer(serializers.ModelSerializer):
    """Serializer for PSD document information."""
    layers = PSDLayerSerializer(many=True, read_only=True)
    user = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = PSDDocument
        fields = ['id', 'title', 'file', 'uploaded_at', 'width', 'height', 'user', 'layers']


class PSDUploadSerializer(serializers.Serializer):
    """Serializer for PSD file upload."""
    title = serializers.CharField(max_length=255)
    file = serializers.FileField()
    
    def validate_file(self, value):
        """Validate that the uploaded file is a PSD file."""
        if not value.name.lower().endswith('.psd'):
            raise serializers.ValidationError("Only PSD files are allowed.")
        
        # Check file size (limit to 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError(f"File size too large. Maximum allowed size is {max_size // (1024*1024)}MB.")
        
        return value


