from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from users.models import Club
from django.conf import settings

# Create your models here.
class Match(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='content')
    match_type = models.CharField(max_length=255, default="League")
    opponent = models.CharField(max_length=255)
    club_logo = models.URLField(blank=True, null=True)
    opponent_logo= models.URLField(blank=True, null=True)
    sponsor = models.URLField(blank=True, null=True)
    date = models.DateTimeField()
    time_start =models.CharField(max_length=20, blank=True, null=True)
    venue = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.club.name} vs {self.opponent} on {self.date.strftime('%Y-%m-%d')}"