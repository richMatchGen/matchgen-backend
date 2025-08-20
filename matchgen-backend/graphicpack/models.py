from django.conf import settings  # ✅ keeps it clean and safe for custom user models
from django.db import models


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

    def __str__(self):
        return f"{self.graphic_pack.name} - {self.content_type}"


class TextElement(models.Model):
    template = models.ForeignKey(
        Template, on_delete=models.CASCADE, related_name="text_elements"
    )
    placeholder = models.CharField(max_length=100)  # e.g., "name", "role", etc.
    primary_font_family = models.CharField(max_length=300)
    secondary_font_family = models.CharField(max_length=300)
    primary_font_size = models.IntegerField()
    secondary_font_size = models.IntegerField()
    primary_text_color = models.CharField(max_length=7)  # Hex like "#FFFFFF"
    secondary_text_color = models.CharField(max_length=7)
    primary_position_x = models.FloatField()  # Percent (0.0 to 1.0) or absolute pixels
    primary_position_y = models.FloatField()
    septenary_position_y = models.FloatField(default=0)
    alignment = models.CharField(
        max_length=20,
        choices=[("left", "Left"), ("center", "Center"), ("right", "Right")],
        default="left",
    )
    max_width = models.FloatField(null=True, blank=True)  # Optional: to wrap text

    def __str__(self):
        return f"{self.template.name} - {self.placeholder}"


class TemplateElement(models.Model):
    template = models.ForeignKey(
        Template, related_name="elements", on_delete=models.CASCADE
    )
    type = models.CharField(
        max_length=10, choices=[("text", "Text"), ("image", "Image")]
    )
    content_key = models.CharField(
        max_length=50, null=True, blank=True
    )  # e.g., "match_title"
    x = models.FloatField()  # Use % or pixel, depending on your rendering logic
    y = models.FloatField()
    width = models.FloatField(blank=True, null=True)  # Only used for images
    height = models.FloatField(blank=True, null=True)
    rotation = models.FloatField(default=0.0)
    
    # New fields for better positioning
    use_percentage = models.BooleanField(default=False)  # Use percentage instead of pixels
    max_width = models.FloatField(blank=True, null=True)  # Maximum width for text wrapping
    z_index = models.IntegerField(default=0)  # Layer order
    visible = models.BooleanField(default=True)  # Show/hide element
    
    class Meta:
        ordering = ['z_index', 'id']


# Text elements
class StringElement(models.Model):
    template = models.ForeignKey(
        TemplateElement, related_name="string_elements", on_delete=models.CASCADE
    )
    content_key = models.CharField(max_length=50)  # e.g., "match_title"
    font_family = models.CharField(max_length=100, default="Arial.ttf")
    font_size = models.IntegerField(default=24)
    color = models.CharField(max_length=7, default="#FFFFFF")
    alignment = models.CharField(
        max_length=10,
        choices=[("left", "Left"), ("center", "Center"), ("right", "Right")],
        default="left",
    )
    max_width = models.FloatField(null=True, blank=True)
    
    # Enhanced text styling
    font_weight = models.CharField(
        max_length=20,
        choices=[("normal", "Normal"), ("bold", "Bold"), ("light", "Light")],
        default="normal"
    )
    font_style = models.CharField(
        max_length=20,
        choices=[("normal", "Normal"), ("italic", "Italic")],
        default="normal"
    )
    text_shadow = models.BooleanField(default=False)
    shadow_color = models.CharField(max_length=7, default="#000000")
    shadow_offset_x = models.IntegerField(default=2)
    shadow_offset_y = models.IntegerField(default=2)
    line_height = models.FloatField(default=1.2)  # Multiplier for line spacing
    letter_spacing = models.FloatField(default=0.0)  # Space between characters


# Image elements
class ImageElement(models.Model):
    template = models.ForeignKey(
        TemplateElement, related_name="image_elements", on_delete=models.CASCADE
    )
    content_key = models.CharField(max_length=50)  # e.g., "team_logo"
    maintain_aspect_ratio = models.BooleanField(default=True)
