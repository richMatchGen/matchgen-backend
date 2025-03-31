from django.urls import path
from .views import MatchListCreateView

urlpatterns = [
    path("matches/", MatchListCreateView.as_view(), name="match-list-create"),
]
