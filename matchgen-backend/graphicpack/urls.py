from django.urls import path
from .views import GraphicPackListView,SelectGraphicPackView,generate_matchday

urlpatterns = [
    path("graphic-packs/", GraphicPackListView.as_view(), name="graphic-pack-list"),
    path("select-pack/", SelectGraphicPackView.as_view(), name="select-pack-list"),
    path("match/<int:match_id>/generate-matchday/", generate_matchday, name="generate-matchday-post"),
]
