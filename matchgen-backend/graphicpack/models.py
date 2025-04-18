from django.db import models
from django.conf import settings  # ✅ keeps it clean and safe for custom user models

class GraphicPack(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    preview_image_url = models.URLField(blank=True, null=True)
    zip_file_url = models.URLField(blank=True, null=True)

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
        ("alert", "Alert"),
        ("player", "Player"),
    ]

    graphic_pack = models.ForeignKey(GraphicPack, on_delete=models.CASCADE, related_name="templates")
    content_type = models.CharField(max_length=100, choices=CONTENT_CHOICES)
    image_url = models.URLField()
    sport = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.graphic_pack.name} - {self.content_type}"


class TextElement(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="text_elements")
    placeholder = models.CharField(max_length=100)  # e.g., "name", "role", etc.
    primary_font_family = models.CharField(max_length=300)
    secondary_font_family = models.CharField(max_length=300)
    primary_font_size = models.IntegerField()
    secondary_font_size = models.IntegerField()
    primary_text_color = models.CharField(max_length=7)  # Hex like "#FFFFFF"
    secondary_text_color = models.CharField(max_length=7)
    primary_position_x = models.FloatField()  # Percent (0.0 to 1.0) or absolute pixels
    primary_position_y = models.FloatField()
    secondary_position_x = models.FloatField()  # Percent (0.0 to 1.0) or absolute pixels
    secondary_position_y = models.FloatField()
    tertiary_position_x = models.FloatField()  # Percent (0.0 to 1.0) or absolute pixels
    tertiary_position_y = models.FloatField()
    quaternary_position_x = models.FloatField()  # Percent (0.0 to 1.0) or absolute pixels
    quaternary_position_y = models.FloatField()
    quinary_position_x = models.FloatField(default=0) # Percent (0.0 to 1.0) or absolute pixels
    quinary_position_y = models.FloatField(default=0)
    senary_position_x = models.FloatField(default=0) # Percent (0.0 to 1.0) or absolute pixels
    senary_position_y = models.FloatField(default=0)
    septenary_position_x = models.FloatField(default=0)  # Percent (0.0 to 1.0) or absolute pixels
    septenary_position_y = models.FloatField(default=0)
    alignment = models.CharField(max_length=20, choices=[("left", "Left"), ("center", "Center"), ("right", "Right")], default="left")
    max_width = models.FloatField(null=True, blank=True)  # Optional: to wrap text

    def __str__(self):
        return f"{self.template.name} - {self.placeholder}"