from django.db import models
from django.conf import settings


class PSDDocument(models.Model):
    """Model to store uploaded PSD document information."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='psd_documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='psd_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    width = models.IntegerField()
    height = models.IntegerField()
    
    def __str__(self):
        return f"{self.title} ({self.width}x{self.height})"


class PSDLayer(models.Model):
    """Model to store individual layer information from PSD files."""
    document = models.ForeignKey(PSDDocument, on_delete=models.CASCADE, related_name='layers')
    name = models.CharField(max_length=255)
    x = models.IntegerField(help_text="X coordinate of layer")
    y = models.IntegerField(help_text="Y coordinate of layer")
    width = models.IntegerField(help_text="Width of layer")
    height = models.IntegerField(help_text="Height of layer")
    visible = models.BooleanField(default=True)
    opacity = models.FloatField(default=100.0)
    layer_type = models.CharField(max_length=50, default='layer')
    
    class Meta:
        ordering = ['y', 'x']  # Order by position for logical display
    
    def __str__(self):
        return f"{self.name} at ({self.x}, {self.y}) - {self.width}x{self.height}"
    
    @property
    def bounding_box(self):
        """Return bounding box as a formatted string."""
        return f"x={self.x}, y={self.y}, w={self.width}, h={self.height}"
