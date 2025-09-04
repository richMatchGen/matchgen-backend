from django.contrib import admin
from .models import PSDDocument, PSDLayer


@admin.register(PSDDocument)
class PSDDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'width', 'height', 'uploaded_at']
    list_filter = ['uploaded_at', 'user']
    search_fields = ['title', 'user__username']
    readonly_fields = ['uploaded_at']


@admin.register(PSDLayer)
class PSDLayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'document', 'x', 'y', 'width', 'height', 'visible', 'opacity']
    list_filter = ['visible', 'layer_type', 'document']
    search_fields = ['name', 'document__title']
    readonly_fields = ['document']
