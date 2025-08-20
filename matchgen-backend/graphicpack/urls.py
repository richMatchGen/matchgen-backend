from django.urls import path

from .views import (
    GraphicPackListView,
    GraphicPackDetailView,
    SelectGraphicPackView,
    ObtainTokenView,
)

urlpatterns = [
    # Basic graphic pack management
    path("packs/", GraphicPackListView.as_view(), name="graphic-pack-list"),
    path("graphic-packs/", GraphicPackListView.as_view(), name="graphic-pack-list-legacy"),
    path("graphic-packs/<int:id>/", GraphicPackDetailView.as_view(), name="graphic-pack-detail"),
    path("select/", SelectGraphicPackView.as_view(), name="select-graphic-pack"),
    path("select-pack/", SelectGraphicPackView.as_view(), name="select-graphic-pack-legacy"),
    
    # Utility endpoints
    path("obtain-token/", ObtainTokenView.as_view(), name="obtain-token"),
]
