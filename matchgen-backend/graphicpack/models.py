from django.conf import settings  # ✅ keeps it clean and safe for custom user models
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class GraphicPack(models.Model):
    TIER_CHOICES = [
        ('basic', 'Basic'),
        ('semipro', 'SemiPro'),
        ('pro', 'Pro'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    preview_image_url = models.URLField(max_length=500, blank=True, null=True)
    zip_file_url = models.URLField(max_length=500, blank=True, null=True)
    
    # New fields for admin functionality
    primary_color = models.CharField(max_length=7, default='#000000', help_text="Primary color for the pack")
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, blank=True, null=True, help_text="Subscription tier required")
    assigned_club = models.ForeignKey('users.Club', on_delete=models.SET_NULL, null=True, blank=True, help_text="Specific club (null for all clubs)")
    is_active = models.BooleanField(default=True, help_text="Whether the pack is active")
    sport = models.CharField(max_length=50, blank=True, null=True, help_text="Sport type for the graphic pack")
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.name


class UserSelection(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    selected_pack = models.ForeignKey(GraphicPack, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username}'s Selection"


class Template(models.Model):
    CONTENT_CHOICES = [
        ("matchday", "Matchday"),
        ("result", "Result"),
        ("lineup", "Lineup"),
        ("fixture", "Fixture"),
        ("upcomingFixtures", "Upcoming Fixtures"),
        ("upcomingFixture", "Upcoming Fixture"),
        ("startingXI", "Starting XI"),
        ("goal", "Goal"),
        ("sub", "Substitution"),
        ("halftime", "Halftime"),
        ("fulltime", "Full-time"),
        ("alert", "Alert"),
        ("player", "Player"),
    ]

    graphic_pack = models.ForeignKey(
        GraphicPack, on_delete=models.CASCADE, related_name="templates"
    )
    content_type = models.CharField(max_length=100, choices=CONTENT_CHOICES)
    image_url = models.URLField(max_length=500)
    sport = models.CharField(max_length=50, blank=True)
    
    # New fields for file management
    file_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL of the uploaded file")
    file_name = models.CharField(max_length=255, blank=True, null=True, help_text="Original filename")
    file_size = models.IntegerField(blank=True, null=True, help_text="File size in bytes")
    
    # New JSON field to store template configuration
    template_config = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    # Example template_config structure:
    # {
    #   "elements": {
    #     "date": {
    #       "type": "text",
    #       "position": { "x": 200, "y": 150 },
    #       "style": {
    #         "fontSize": 24,
    #         "fontFamily": "Arial",
    #         "color": "#FFFFFF",
    #         "alignment": "center"
    #       }
    #     },
    #     "time": {
    #       "type": "text", 
    #       "position": { "x": 400, "y": 150 },
    #       "style": {
    #         "fontSize": 24,
    #         "fontFamily": "Arial", 
    #         "color": "#FFFFFF",
    #         "alignment": "center"
    #       }
    #     }
    #   }
    # }

    def __str__(self):
        return f"{self.graphic_pack.name} - {self.content_type}"


class TextElement(models.Model):
    """Text and image element configuration for graphic packs."""
    graphic_pack = models.ForeignKey(GraphicPack, on_delete=models.CASCADE, related_name='text_elements')
    content_type = models.CharField(max_length=50, help_text="e.g., matchday, upcoming, startingxi")
    element_name = models.CharField(max_length=50, help_text="e.g., date, time, venue, opponent, logo")
    
    # Element type
    element_type = models.CharField(
        max_length=10,
        choices=[('text', 'Text'), ('image', 'Image')],
        default='text',
        help_text="Type of element to render"
    )
    
    # Position
    position_x = models.IntegerField(default=400, validators=[MinValueValidator(0), MaxValueValidator(2000)])
    position_y = models.IntegerField(default=150, validators=[MinValueValidator(0), MaxValueValidator(2000)])
    
    # Multiple anchor positions for text elements (from PSD processing)
    top_left_x = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Top-left X position for left alignment")
    top_left_y = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Top-left Y position for left alignment")
    top_center_x = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Top-center X position for center alignment")
    top_center_y = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Top-center Y position for center alignment")
    top_right_x = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Top-right X position for right alignment")
    top_right_y = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Top-right Y position for right alignment")
    
    # Bottom anchor positions for text elements
    bottom_left_x = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Bottom-left X position for left alignment")
    bottom_left_y = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Bottom-left Y position for left alignment")
    bottom_center_x = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Bottom-center X position for center alignment")
    bottom_center_y = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Bottom-center Y position for center alignment")
    bottom_right_x = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Bottom-right X position for right alignment")
    bottom_right_y = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Bottom-right Y position for right alignment")
    
    # Center anchor positions for text elements
    center_left_x = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Center-left X position for left alignment")
    center_left_y = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Center-left Y position for left alignment")
    center_center_x = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Center-center X position for center alignment")
    center_center_y = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Center-center Y position for center alignment")
    center_right_x = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Center-right X position for right alignment")
    center_right_y = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Center-right Y position for right alignment")
    
    # Home/Away specific positioning for images
    home_position_x = models.IntegerField(default=400, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="X position for home fixtures")
    home_position_y = models.IntegerField(default=150, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Y position for home fixtures")
    away_position_x = models.IntegerField(default=400, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="X position for away fixtures")
    away_position_y = models.IntegerField(default=150, validators=[MinValueValidator(0), MaxValueValidator(2000)], help_text="Y position for away fixtures")
    
    # Font settings
    font_size = models.IntegerField(default=24, validators=[MinValueValidator(8)])
    font_family = models.CharField(max_length=100, default='Arial')
    font_color = models.CharField(max_length=7, default='#FFFFFF', help_text="Hex color code")
    
    # Text alignment
    alignment = models.CharField(
        max_length=10, 
        choices=[('left', 'Left'), ('center', 'Center'), ('right', 'Right')],
        default='center'
    )
    
    # Text alignment within the element (separate from positioning)
    text_alignment = models.CharField(
        max_length=10,
        choices=[('left', 'Left'), ('center', 'Center'), ('right', 'Right')],
        default='center',
        help_text="How text is aligned within the element bounds"
    )
    
    # Position anchor (top or bottom)
    position_anchor = models.CharField(
        max_length=10,
        choices=[('top', 'Top'), ('bottom', 'Bottom')],
        default='top',
        help_text="Whether to use top or bottom anchor points for positioning"
    )
    
    # Anchor point is now determined by alignment choice and position_anchor (left=lt/lb, center=mt/mb, right=rt/rb)
    
    # Optional settings
    font_weight = models.CharField(
        max_length=20,
        choices=[('normal', 'Normal'), ('bold', 'Bold')],
        default='normal'
    )
    
    # Image-specific settings
    image_width = models.IntegerField(default=100, validators=[MinValueValidator(10), MaxValueValidator(500)], help_text="Width of image in pixels")
    image_height = models.IntegerField(default=100, validators=[MinValueValidator(10), MaxValueValidator(500)], help_text="Height of image in pixels")
    maintain_aspect_ratio = models.BooleanField(default=True, help_text="Maintain aspect ratio when resizing image")
    
    # Image color modification settings
    image_color_filter = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Filter'),
            ('grayscale', 'Grayscale'),
            ('sepia', 'Sepia'),
            ('invert', 'Invert Colors'),
            ('custom', 'Custom Color')
        ],
        default='none',
        help_text="Color filter to apply to image"
    )
    image_color_tint = models.CharField(
        max_length=7, 
        default='#FFFFFF', 
        help_text="Hex color for tinting (use with custom filter)"
    )
    image_brightness = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(3.0)],
        help_text="Brightness multiplier (0.1 to 3.0)"
    )
    image_contrast = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(3.0)],
        help_text="Contrast multiplier (0.1 to 3.0)"
    )
    image_saturation = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(3.0)],
        help_text="Saturation multiplier (0.0 to 3.0)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['graphic_pack', 'content_type', 'element_name']
        ordering = ['graphic_pack', 'content_type', 'element_name']
    
    def __str__(self):
        return f"{self.graphic_pack.name} - {self.content_type} - {self.element_name}"
    
    @property
    def position(self):
        return {'x': self.position_x, 'y': self.position_y}
    
    @property
    def style(self):
        if self.element_type == 'text':
            return {
                'fontSize': self.font_size,
                'fontFamily': self.font_family,
                'color': self.font_color,
                'alignment': self.alignment,
                'fontWeight': self.font_weight
            }
        else:  # image
            return {
                'width': self.image_width,
                'height': self.image_height,
                'maintainAspectRatio': self.maintain_aspect_ratio,
                'colorFilter': self.image_color_filter,
                'colorTint': self.image_color_tint,
                'brightness': self.image_brightness,
                'contrast': self.image_contrast,
                'saturation': self.image_saturation
            }
