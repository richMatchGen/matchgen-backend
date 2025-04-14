from django.urls import path
from .views import GraphicPackListView,SelectGraphicPackView

urlpatterns = [
    path("graphic-packs/", GraphicPackListView.as_view(), name="graphic-pack-list"),
    path("select-pack/", SelectGraphicPackView.as_view(), name="select-pack-list"),
]
