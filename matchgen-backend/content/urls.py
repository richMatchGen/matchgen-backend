from django.urls import path
from .views import MatchListCreateView,PlayerListCreateView

urlpatterns = [
    path("matches/", MatchListCreateView.as_view(), name="match-list-create"),
    path("players/", PlayerListCreateView.as_view(), name="player-list-create"),
]
