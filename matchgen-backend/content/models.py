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
    SOURCE_CHOICES = [
        ("fulltime_html", "FA Full-Time (HTML via proxy)"),
        ("upload", "CSV/XLSX Upload"),
        ("manual", "Manual"),
        ("ai_import", "AI Import"),
        ("other", "Other"),
    ]
    
    HOME_AWAY_CHOICES = [
        ('HOME', 'Home'),
        ('AWAY', 'Away'),
    ]
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="matches")
    
    # Source tracking
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES, default="manual")
    source_team_id = models.CharField(max_length=32, blank=True, null=True)   # e.g. 562720767
    source_competition_url = models.URLField(blank=True, null=True)
    
    # Identity
    fixture_key = models.CharField(max_length=128, db_index=True, blank=True, null=True)  # stable key for upsert
    competition = models.CharField(max_length=128, blank=True, default="")
    round_name = models.CharField(max_length=128, blank=True, default="")
    
    # Teams
    home_team = models.CharField(max_length=128, blank=True, default="")
    away_team = models.CharField(max_length=128, blank=True, default="")
    home_away = models.CharField(max_length=4, choices=HOME_AWAY_CHOICES, default='HOME')
    opponent = models.CharField(max_length=255)
    
    # Timing
    date = models.DateTimeField()
    time_start = models.CharField(max_length=20, blank=True, null=True)
    kickoff_utc = models.DateTimeField(blank=True, null=True)
    kickoff_local_tz = models.CharField(max_length=64, default="Europe/London")
    
    # Location
    venue = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    
    # Status + score
    status = models.CharField(max_length=32, default="SCHEDULED")  # SCHEDULED|LIVE|FT|POSTPONED
    score_home = models.IntegerField(blank=True, null=True)
    score_away = models.IntegerField(blank=True, null=True)
    
    # Legacy fields
    match_type = models.CharField(max_length=255, default="League")
    club_logo = models.URLField(max_length=500, blank=True, null=True)
    opponent_logo = models.URLField(max_length=500, blank=True, null=True)
    sponsor = models.URLField(max_length=500, blank=True, null=True)
    matchday_post_url = models.URLField(max_length=500, blank=True, null=True)
    upcoming_fixture_post_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL for uploaded upcoming fixture post")
    starting_xi_post_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL for uploaded starting XI post")
    
    # Raw data and sync tracking
    raw_payload = models.JSONField(blank=True, null=True)
    last_synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("club", "fixture_key")]

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
    
    # Admin-uploaded bespoke graphics
    cutout_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL for uploaded player cutout image")
    highlight_home_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL for uploaded highlight image (Home)")
    highlight_away_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL for uploaded highlight image (Away)")
    potm_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL for uploaded Player of the Match image")

    def __str__(self):
        return self.name


class FullTimeSubscription(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="fulltime_sources")
    competition_url = models.URLField()  # pasted by admin
    team_display_name = models.CharField(max_length=128)  # "Leafield Athletic Women" for H/A inference
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.club.name} - {self.team_display_name}"
