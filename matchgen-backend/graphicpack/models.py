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
