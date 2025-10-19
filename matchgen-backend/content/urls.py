from django.urls import path

from .views import (
    LastMatchView,
    MatchdayView,
    MatchListCreateView,
    MatchListView,
    MatchDetailView,
    OpponentLogoUploadView,
    PlayerListCreateView,
    PlayerDetailView,
    PlayerPhotoUploadView,
    SubstitutionPlayersView,
    UpcomingMatchView,
    FAFulltimeScraperView,
    PlayCricketAPIView,
    EnhancedBulkUploadMatchesView,
    FixtureImportOptionsView,
    FAFulltimeTestView,
    AIFixtureImportView,
    AIFixtureTestView,
    fulltime_preview,
    fulltime_import,
)

urlpatterns = [
    path("matches/", MatchListCreateView.as_view(), name="match-list-create"),
    path("matches/<int:pk>/", MatchDetailView.as_view(), name="match-detail"),
    path("players/", PlayerListCreateView.as_view(), name="player-list-create"),
    path("players/<int:id>/", PlayerDetailView.as_view(), name="player-detail"),
    path("matches/last/", LastMatchView.as_view(), name="last-match"),
    path("matches/matchday/", MatchdayView.as_view(), name="match-day"),
    path("matches/upcoming/", UpcomingMatchView.as_view(), name="fixture"),
    path("fixtures/", MatchListView.as_view(), name="fixtures"),
    path("players/substitution/", SubstitutionPlayersView.as_view(), name="substitution-players"),
    path("matches/upload-opponent-logo/", OpponentLogoUploadView.as_view(), name="upload-opponent-logo"),
    path("players/upload-photo/", PlayerPhotoUploadView.as_view(), name="upload-player-photo"),
    # New fixture import endpoints
    path("fixtures/import-options/", FixtureImportOptionsView.as_view(), name="fixture-import-options"),
    path("fixtures/import/csv/", EnhancedBulkUploadMatchesView.as_view(), name="fixture-import-csv"),
    path("fixtures/import/fa-fulltime/", FAFulltimeScraperView.as_view(), name="fixture-import-fa"),
    path("fixtures/import/fa-fulltime/test/", FAFulltimeTestView.as_view(), name="fixture-import-fa-test"),
    path("fixtures/import/play-cricket/", PlayCricketAPIView.as_view(), name="fixture-import-cricket"),
    path("fixtures/import/ai/", AIFixtureImportView.as_view(), name="fixture-import-ai"),
    path("fixtures/import/ai/test/", AIFixtureTestView.as_view(), name="fixture-import-ai-test"),
    # New FA Fulltime proxy endpoints
    path("fixtures/import/fulltime/preview/", fulltime_preview, name="fulltime-preview"),
    path("fixtures/import/fulltime/import/", fulltime_import, name="fulltime-import"),
]
