from django.urls import path

from .views import (
    GraphicGenerationView,
    GraphicPackListView,
    ObtainTokenView,
    RegenerateGraphicView,
    SelectGraphicPackView,
    TemplateEditorView,
    DebugGraphicPackView,
    TestAPIView,
    CreateTestDataView,
    generate_matchday,
)

urlpatterns = [
    path("packs/", GraphicPackListView.as_view(), name="graphic-pack-list"),
    path("graphic-packs/", GraphicPackListView.as_view(), name="graphic-pack-list-legacy"),  # Backward compatibility
    path("select/", SelectGraphicPackView.as_view(), name="select-graphic-pack"),
    path("select-pack/", SelectGraphicPackView.as_view(), name="select-graphic-pack-legacy"),  # Backward compatibility
    path("generate/", GraphicGenerationView.as_view(), name="generate-graphic"),
    path("regenerate/", RegenerateGraphicView.as_view(), name="regenerate-graphic"),
    path("template/<int:template_id>/edit/", TemplateEditorView.as_view(), name="template-editor"),
    path("debug/", DebugGraphicPackView.as_view(), name="debug-graphic-pack"),
    path("test/", TestAPIView.as_view(), name="test-api"),
    path("create-test-data/", CreateTestDataView.as_view(), name="create-test-data"),
    
    # Individual post type endpoints
    path("match/<int:match_id>/generate-upcoming/", GraphicGenerationView.as_view(), name="generate-upcoming"),
    path("match/<int:match_id>/generate-startingxi/", GraphicGenerationView.as_view(), name="generate-startingxi"),
    path("match/<int:match_id>/generate-goal/", GraphicGenerationView.as_view(), name="generate-goal"),
    path("match/<int:match_id>/generate-substitution/", GraphicGenerationView.as_view(), name="generate-substitution"),
    path("match/<int:match_id>/generate-halftime/", GraphicGenerationView.as_view(), name="generate-halftime"),
    path("match/<int:match_id>/generate-fulltime/", GraphicGenerationView.as_view(), name="generate-fulltime"),
    path("match/<int:match_id>/generate-matchday/", GraphicGenerationView.as_view(), name="generate-matchday"),
    
    # Legacy endpoint
    path("generate-matchday/<int:match_id>/", generate_matchday, name="generate-matchday-legacy"),
    path("obtain-token/", ObtainTokenView.as_view(), name="obtain-token"),
]
