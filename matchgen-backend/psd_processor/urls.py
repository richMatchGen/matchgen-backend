from django.urls import path
from . import views

app_name = 'psd_processor'

urlpatterns = [
    path('upload/', views.PSDUploadView.as_view(), name='psd_upload'),
    path('documents/', views.PSDDocumentListView.as_view(), name='psd_document_list'),
    path('documents/<int:document_id>/', views.PSDDocumentDetailView.as_view(), name='psd_document_detail'),
    path('documents/<int:document_id>/layers/', views.PSDLayerListView.as_view(), name='psd_layer_list'),
    path('documents/<int:document_id>/delete/', views.delete_psd_document, name='psd_document_delete'),
]








