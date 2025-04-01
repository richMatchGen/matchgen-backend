from rest_framework import serializers
from .models import Match, Player

class MatchSerializer(serializers.ModelSerializer):
    formatted_date = serializers.SerializerMethodField()
    class Meta:
        model = Match
        fields = [
            "match_type", "opponent", "club_logo", "opponent_logo", "sponsor",
            "date","formatted_date" ,"time_start", "venue", "location"
        ]

    def get_formatted_date(self, obj):
        return obj.date.strftime("%d/%m/%Y")
    

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = [
            "name", "squad_no", "player_pic", "formatted_pic", "position",
            "sponsor"
        ]