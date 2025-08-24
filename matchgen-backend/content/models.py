from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from users.models import Club, User


# Create your models here.
class Match(models.Model):
    HOME_AWAY_CHOICES = [
        ('HOME', 'Home'),
        ('AWAY', 'Away'),
    ]
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="matches")
    match_type = models.CharField(max_length=255, default="League")
    opponent = models.CharField(max_length=255)
    home_away = models.CharField(max_length=4, choices=HOME_AWAY_CHOICES, default='HOME')
    club_logo = models.URLField(max_length=500, blank=True, null=True)
    opponent_logo = models.URLField(max_length=500, blank=True, null=True)
    sponsor = models.URLField(max_length=500, blank=True, null=True)
    date = models.DateTimeField()
    time_start = models.CharField(max_length=20, blank=True, null=True)
    venue = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    matchday_post_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return (
            f"{self.club.name} vs {self.opponent} on {self.date.strftime('%Y-%m-%d')}"
        )


# Create your models here.
class Player(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="players")
    name = models.CharField(max_length=255)
    squad_no = models.CharField(max_length=4)
    player_pic = models.URLField(max_length=500, blank=True, null=True)
    formatted_pic = models.URLField(max_length=500, blank=True, null=True)
    sponsor = models.URLField(max_length=500, blank=True, null=True)
    position = models.CharField(max_length=255)

    def __str__(self):
        return self.name
