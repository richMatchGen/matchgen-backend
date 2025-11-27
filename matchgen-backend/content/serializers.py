from rest_framework import serializers

from .models import Match, Player


class MatchSerializer(serializers.ModelSerializer):
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            "id",
            "club",
            "match_type",
            "opponent",
            "home_away",
            "club_logo",
            "opponent_logo",
            "sponsor",
            "date",
            "formatted_date",
            "time_start",
            "venue",
            "location",
            "matchday_post_url",
            "upcoming_fixture_post_url",
            "starting_xi_post_url",
            "halftime_post_url",
            "fulltime_post_url",
        ]
        read_only_fields = ["id", "club"]  # club is set by the view, not the client

    def get_formatted_date(self, obj):
        return obj.date.strftime("%d/%m/%Y")


class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = [
            "id",
            "club",
            "name",
            "squad_no",
            "player_pic",
            "formatted_pic",
            "position",
            "sponsor",
            "cutout_url",
            "highlight_home_url",
            "highlight_away_url",
            "potm_url",
        ]
        read_only_fields = ["id", "club"]  # club is set by the view, not the client


class FixturesSerializer(serializers.ModelSerializer):
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            "id",
            "club",
            "match_type",
            "opponent",
            "home_away",
            "club_logo",
            "opponent_logo",
            "sponsor",
            "date",
            "formatted_date",
            "time_start",
            "venue",
            "location",
            "matchday_post_url",
            "upcoming_fixture_post_url",
            "starting_xi_post_url",
            "halftime_post_url",
            "fulltime_post_url",
        ]
        read_only_fields = ["id", "club"]

    def get_formatted_date(self, obj):
        return obj.date.strftime("%d/%m/%Y")
