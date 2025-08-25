from django.urls import path

from .views import (
    LastMatchView,
    MatchdayView,
    MatchListCreateView,
    MatchListView,
    MatchDetailView,
    PlayerListCreateView,
    SubstitutionPlayersView,
    UpcomingMatchView,
)

urlpatterns = [
    path("matches/", MatchListCreateView.as_view(), name="match-list-create"),
    path("matches/<int:pk>/", MatchDetailView.as_view(), name="match-detail"),
    path("players/", PlayerListCreateView.as_view(), name="player-list-create"),
    path("matches/last/", LastMatchView.as_view(), name="last-match"),
    path("matches/matchday/", MatchdayView.as_view(), name="match-day"),
    path("matches/upcoming/", UpcomingMatchView.as_view(), name="fixture"),
    path("fixtures/", MatchListView.as_view(), name="fixtures"),
    path("players/substitution/", SubstitutionPlayersView.as_view(), name="substitution-players"),
]
