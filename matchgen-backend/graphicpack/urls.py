from django.urls import path

from .views import (
    GraphicGenerationView,
    GraphicPackListView,
    ObtainTokenView,
    SelectGraphicPackView,
    generate_matchday,
)

urlpatterns = [
    path("packs/", GraphicPackListView.as_view(), name="graphic-pack-list"),
    path("graphic-packs/", GraphicPackListView.as_view(), name="graphic-pack-list-legacy"),  # Backward compatibility
    path("select/", SelectGraphicPackView.as_view(), name="select-graphic-pack"),
    path("generate/", GraphicGenerationView.as_view(), name="generate-graphic"),
    path("generate-matchday/<int:match_id>/", generate_matchday, name="generate-matchday"),
    path("token/", ObtainTokenView.as_view(), name="obtain-token"),
]
