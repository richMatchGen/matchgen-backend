from django.conf import settings  # ✅ keeps it clean and safe for custom user models
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class GraphicPack(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    preview_image_url = models.URLField(max_length=500, blank=True, null=True)
    zip_file_url = models.URLField(max_length=500, blank=True, null=True)

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
    
    # New JSON field to store template configuration
    template_config = models.JSONField(default=dict, blank=True)
    
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
    """Text element configuration for graphic packs."""
    graphic_pack = models.ForeignKey(GraphicPack, on_delete=models.CASCADE, related_name='text_elements')
    content_type = models.CharField(max_length=50, help_text="e.g., matchday, upcoming, startingxi")
    element_name = models.CharField(max_length=50, help_text="e.g., date, time, venue, opponent")
    
    # Position
    position_x = models.IntegerField(default=400, validators=[MinValueValidator(0), MaxValueValidator(2000)])
    position_y = models.IntegerField(default=150, validators=[MinValueValidator(0), MaxValueValidator(2000)])
    
    # Font settings
    font_size = models.IntegerField(default=24, validators=[MinValueValidator(8), MaxValueValidator(100)])
    font_family = models.CharField(max_length=100, default='Arial')
    font_color = models.CharField(max_length=7, default='#FFFFFF', help_text="Hex color code")
    
    # Text alignment
    alignment = models.CharField(
        max_length=10, 
        choices=[('left', 'Left'), ('center', 'Center'), ('right', 'Right')],
        default='center'
    )
    
    # Optional settings
    font_weight = models.CharField(
        max_length=20,
        choices=[('normal', 'Normal'), ('bold', 'Bold')],
        default='normal'
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
        return {
            'fontSize': self.font_size,
            'fontFamily': self.font_family,
            'color': self.font_color,
            'alignment': self.alignment,
            'fontWeight': self.font_weight
        }
