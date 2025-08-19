from django.urls import path

from .views import (
    GraphicGenerationView,
    GraphicPackListView,
    ObtainTokenView,
    RegenerateGraphicView,
    SelectGraphicPackView,
    generate_matchday,
)

urlpatterns = [
    path("packs/", GraphicPackListView.as_view(), name="graphic-pack-list"),
    path("graphic-packs/", GraphicPackListView.as_view(), name="graphic-pack-list-legacy"),  # Backward compatibility
    path("select/", SelectGraphicPackView.as_view(), name="select-graphic-pack"),
    path("select-pack/", SelectGraphicPackView.as_view(), name="select-graphic-pack-legacy"),  # Backward compatibility
    path("generate/", GraphicGenerationView.as_view(), name="generate-graphic"),
    path("regenerate/", RegenerateGraphicView.as_view(), name="regenerate-graphic"),  # New regenerate endpoint
    path("generate-matchday/<int:match_id>/", generate_matchday, name="generate-matchday"),
    path("match/<int:match_id>/generate-matchday/", generate_matchday, name="generate-matchday-legacy"),  # Backward compatibility
    path("token/", ObtainTokenView.as_view(), name="obtain-token"),
]
