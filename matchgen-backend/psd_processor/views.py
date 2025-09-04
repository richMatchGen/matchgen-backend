import os
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from psd_tools import PSDImage
from .models import PSDDocument, PSDLayer
from .serializers import PSDDocumentSerializer, PSDUploadSerializer, PSDLayerSerializer


class PSDUploadView(APIView):
    """Handle PSD file uploads and process them to extract layer information."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Upload and process a PSD file."""
        serializer = PSDUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the uploaded file and title
            psd_file = request.FILES['file']
            title = serializer.validated_data['title']
            
            # Save the file temporarily
            file_path = default_storage.save(f'psd_files/{psd_file.name}', ContentFile(psd_file.read()))
            full_path = os.path.join(settings.MEDIA_ROOT, file_path)
            
            # Process the PSD file
            psd = PSDImage.open(full_path)
            
            # Create PSD document record
            psd_doc = PSDDocument.objects.create(
                user=request.user,
                title=title,
                file=file_path,
                width=psd.width,
                height=psd.height
            )
            
            # Extract layer information
            layers_data = self._extract_layers(psd)
            
            # Create layer records
            for layer_data in layers_data:
                PSDLayer.objects.create(
                    document=psd_doc,
                    **layer_data
                )
            
            # Clean up temporary file
            if os.path.exists(full_path):
                os.remove(full_path)
            
            # Return the processed document with layers
            result_serializer = PSDDocumentSerializer(psd_doc)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process PSD file: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _extract_layers(self, psd):
        """Extract layer information from PSD file."""
        layers_data = []
        
        def process_layer(layer, parent_name=""):
            """Recursively process layers and groups."""
            if hasattr(layer, 'layers'):
                # This is a group
                for sub_layer in layer.layers:
                    process_layer(sub_layer, f"{parent_name}{layer.name}/" if parent_name else f"{layer.name}/")
            else:
                # This is a regular layer
                if hasattr(layer, 'bbox') and layer.bbox:
                    bbox = layer.bbox
                    layer_data = {
                        'name': f"{parent_name}{layer.name}" if parent_name else layer.name,
                        'x': bbox[0],
                        'y': bbox[1],
                        'width': bbox[2] - bbox[0],
                        'height': bbox[3] - bbox[1],
                        'visible': layer.visible,
                        'opacity': layer.opacity * 100 if hasattr(layer, 'opacity') else 100.0,
                        'layer_type': 'group' if hasattr(layer, 'layers') else 'layer'
                    }
                    layers_data.append(layer_data)
        
        # Process all top-level layers
        for layer in psd.layers:
            process_layer(layer)
        
        return layers_data


class PSDDocumentListView(APIView):
    """List all PSD documents for the authenticated user."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get list of user's PSD documents."""
        documents = PSDDocument.objects.filter(user=request.user).order_by('-uploaded_at')
        serializer = PSDDocumentSerializer(documents, many=True)
        return Response(serializer.data)


class PSDDocumentDetailView(APIView):
    """Get detailed information about a specific PSD document."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, document_id):
        """Get PSD document details with layers."""
        try:
            document = PSDDocument.objects.get(id=document_id, user=request.user)
            serializer = PSDDocumentSerializer(document)
            return Response(serializer.data)
        except PSDDocument.DoesNotExist:
            return Response(
                {'error': 'PSD document not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class PSDLayerListView(APIView):
    """Get all layers for a specific PSD document."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, document_id):
        """Get layers for a specific PSD document."""
        try:
            document = PSDDocument.objects.get(id=document_id, user=request.user)
            layers = document.layers.all()
            serializer = PSDLayerSerializer(layers, many=True)
            return Response(serializer.data)
        except PSDDocument.DoesNotExist:
            return Response(
                {'error': 'PSD document not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_psd_document(request, document_id):
    """Delete a PSD document and all its layers."""
    try:
        document = PSDDocument.objects.get(id=document_id, user=request.user)
        
        # Delete the file
        if document.file:
            default_storage.delete(document.file.name)
        
        # Delete the document (this will cascade delete layers)
        document.delete()
        
        return Response({'message': 'PSD document deleted successfully'})
    except PSDDocument.DoesNotExist:
        return Response(
            {'error': 'PSD document not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
