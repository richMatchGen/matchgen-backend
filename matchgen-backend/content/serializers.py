from rest_framework import serializers
from .models import Match

class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = [
            "match_type", "opponent", "club_logo", "opponent_logo", "sponsor",
            "date", "time_start", "venue", "location"
        ]