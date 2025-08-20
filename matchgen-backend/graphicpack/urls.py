from django.urls import path

from .views import (
    GraphicPackListView,
    GraphicPackDetailView,
    SelectGraphicPackView,
    MatchdayPostGenerator,
    DebugTemplatesView,
    TestEndpointView,
    CreateTestDataView,
    ObtainTokenView,
)

urlpatterns = [
    # Basic graphic pack management
    path("packs/", GraphicPackListView.as_view(), name="graphic-pack-list"),
    path("graphic-packs/", GraphicPackListView.as_view(), name="graphic-pack-list-legacy"),
    path("graphic-packs/<int:id>/", GraphicPackDetailView.as_view(), name="graphic-pack-detail"),
    path("select/", SelectGraphicPackView.as_view(), name="select-graphic-pack"),
    path("select-pack/", SelectGraphicPackView.as_view(), name="select-graphic-pack-legacy"),
    
    # Social media post generation
    path("generate-matchday-post/", MatchdayPostGenerator.as_view(), name="generate-matchday-post"),
    
    # Debug endpoints
    path("debug-templates/", DebugTemplatesView.as_view(), name="debug-templates"),
    path("test/", TestEndpointView.as_view(), name="test"),
    path("create-test-data/", CreateTestDataView.as_view(), name="create-test-data"),
    
    # Utility endpoints
    path("obtain-token/", ObtainTokenView.as_view(), name="obtain-token"),
]
