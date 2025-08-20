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
