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
    DiagnosticView,
    SimpleTestView,
    TemplateDebugView,
    TextElementListView, TextElementCreateView, TextElementUpdateView, 
    TextElementDeleteView, TextElementByGraphicPackView, AddOpponentLogoElementView
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
    path("diagnostic/", DiagnosticView.as_view(), name="diagnostic"),
    path("simple-test/", SimpleTestView.as_view(), name="simple-test"),
    path("template-debug/", TemplateDebugView.as_view(), name="template-debug"),
    
    # Utility endpoints
    path("obtain-token/", ObtainTokenView.as_view(), name="obtain-token"),
    
    # Text Element Management
    path('text-elements/', TextElementListView.as_view(), name='text-element-list'),
    path('text-elements/create/', TextElementCreateView.as_view(), name='text-element-create'),
    path('text-elements/<int:element_id>/update/', TextElementUpdateView.as_view(), name='text-element-update'),
    path('text-elements/<int:element_id>/delete/', TextElementDeleteView.as_view(), name='text-element-delete'),
    path('text-elements/<int:graphic_pack_id>/<str:content_type>/', TextElementByGraphicPackView.as_view(), name='text-element-by-pack'),
    path('add-opponent-logo-element/', AddOpponentLogoElementView.as_view(), name='add-opponent-logo-element'),
]
