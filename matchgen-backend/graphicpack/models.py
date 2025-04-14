from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from users.models import User
from django.conf import settings

# Create your models here.
class GraphicPack(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    preview_image_url = models.URLField(blank=True, null=True)
    zip_file_url = models.URLField(blank=True, null=True)

class UserSelection(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    selected_pack = models.ForeignKey(GraphicPack, on_delete=models.SET_NULL, null=True)


class Template(models.Model):
    CONTENT_CHOICES = [
        ("matchday", "Matchday"),
        ("result", "Result"),
        ("lineup", "Lineup"),
        ("fixture", "Fixture"),
        ("upcomingFixtures", "Upcoming Fixtures"),
        ("lineup", "Lineup"),
        ("alert", "Alert"),
        ("player", "Player"),
        # more as needed
    ]

    graphic_pack = models.ForeignKey(GraphicPack, on_delete=models.CASCADE, related_name="templates")
    content_type = models.CharField(max_length=100, choices=CONTENT_CHOICES)
    image_url = models.URLField()
    sport = models.CharField(max_length=50, blank=True)  # optional per-template tag

    def __str__(self):
        return f"{self.graphic_pack.name} - {self.content_type}"