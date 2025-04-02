from django.urls import path
from .views import MatchListCreateView,PlayerListCreateView,LastMatchView,MatchdayView

urlpatterns = [
    path("matches/", MatchListCreateView.as_view(), name="match-list-create"),
    path("players/", PlayerListCreateView.as_view(), name="player-list-create"),
    path('matches/last/', LastMatchView.as_view(), name='last-match'),
    path('matches/matchday/', MatchdayView.as_view(), name='match-day')
]
