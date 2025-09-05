import os
import tempfile
import logging
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

logger = logging.getLogger(__name__)


class PSDUploadView(APIView):
    """Handle PSD file uploads and process them to extract layer information."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Upload and process a PSD file."""
        serializer = PSDUploadSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"PSD upload validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        temp_file_path = None
        try:
            # Get the uploaded file and title
            psd_file = request.FILES['file']
            title = serializer.validated_data['title']
            
            logger.info(f"Processing PSD file: {psd_file.name} for user {request.user.id}")
            
            # Create a temporary file to process the PSD
            with tempfile.NamedTemporaryFile(delete=False, suffix='.psd') as temp_file:
                # Write the uploaded file content to temporary file
                for chunk in psd_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            # Process the PSD file
            try:
                psd = PSDImage.open(temp_file_path)
                logger.info(f"PSD file opened successfully. Dimensions: {psd.width}x{psd.height}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to open PSD file: {error_msg}")
                
                # Provide user-friendly error messages for common issues
                if "Invalid version 8" in error_msg:
                    user_error = "This PSD file uses a newer format (version 8) that is not yet supported. Please save your PSD file in an older format (version 7 or earlier) or export it as a different format."
                elif "Invalid version" in error_msg:
                    user_error = f"This PSD file uses an unsupported version. {error_msg}"
                elif "not a PSD file" in error_msg.lower():
                    user_error = "The uploaded file does not appear to be a valid PSD file."
                else:
                    user_error = f"Unable to process PSD file: {error_msg}"
                
                return Response(
                    {'error': user_error}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Save the file to permanent storage
            psd_file.seek(0)  # Reset file pointer
            file_path = default_storage.save(f'psd_files/{psd_file.name}', ContentFile(psd_file.read()))
            
            # Create PSD document record
            psd_doc = PSDDocument.objects.create(
                user=request.user,
                title=title,
                file=file_path,
                width=psd.width,
                height=psd.height
            )
            
            logger.info(f"Created PSD document with ID: {psd_doc.id}")
            
            # Extract layer information
            try:
                layers_data = self._extract_layers(psd)
                logger.info(f"Extracted {len(layers_data)} layers from PSD file")
            except Exception as e:
                logger.error(f"Failed to extract layers: {str(e)}")
                # Don't fail the upload if layer extraction fails
                layers_data = []
            
            # Create layer records
            for layer_data in layers_data:
                try:
                    PSDLayer.objects.create(
                        document=psd_doc,
                        **layer_data
                    )
                except Exception as e:
                    logger.error(f"Failed to create layer {layer_data.get('name', 'unknown')}: {str(e)}")
                    # Continue with other layers
            
            # Return the processed document with layers
            result_serializer = PSDDocumentSerializer(psd_doc)
            logger.info(f"PSD upload completed successfully for document {psd_doc.id}")
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"PSD upload failed: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to process PSD file: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    logger.error(f"Failed to clean up temporary file: {str(e)}")
    
    def _extract_layers(self, psd):
        """Extract layer information from PSD file."""
        layers_data = []
        
        def process_layer(layer, parent_name=""):
            """Recursively process layers and groups."""
            try:
                if hasattr(layer, 'layers') and layer.layers:
                    # This is a group
                    for sub_layer in layer.layers:
                        process_layer(sub_layer, f"{parent_name}{layer.name}/" if parent_name else f"{layer.name}/")
                else:
                    # This is a regular layer
                    layer_name = f"{parent_name}{layer.name}" if parent_name else layer.name
                    
                    # Get bounding box safely
                    bbox = None
                    if hasattr(layer, 'bbox') and layer.bbox:
                        bbox = layer.bbox
                    elif hasattr(layer, 'left') and hasattr(layer, 'top') and hasattr(layer, 'right') and hasattr(layer, 'bottom'):
                        bbox = (layer.left, layer.top, layer.right, layer.bottom)
                    
                    if bbox and len(bbox) >= 4:
                        # Calculate dimensions
                        x = int(bbox[0]) if bbox[0] is not None else 0
                        y = int(bbox[1]) if bbox[1] is not None else 0
                        width = int(bbox[2] - bbox[0]) if bbox[2] is not None and bbox[0] is not None else 0
                        height = int(bbox[3] - bbox[1]) if bbox[3] is not None and bbox[1] is not None else 0
                        
                        # Get visibility and opacity safely
                        visible = getattr(layer, 'visible', True)
                        opacity = getattr(layer, 'opacity', 1.0)
                        if isinstance(opacity, (int, float)) and opacity <= 1.0:
                            opacity = opacity * 100
                        
                        layer_data = {
                            'name': layer_name,
                            'x': x,
                            'y': y,
                            'width': width,
                            'height': height,
                            'visible': bool(visible),
                            'opacity': float(opacity),
                            'layer_type': 'group' if hasattr(layer, 'layers') and layer.layers else 'layer'
                        }
                        layers_data.append(layer_data)
                        logger.debug(f"Extracted layer: {layer_name} at ({x}, {y}) - {width}x{height}")
                    else:
                        logger.warning(f"Could not extract bounding box for layer: {layer_name}")
                        
            except Exception as e:
                logger.error(f"Error processing layer {getattr(layer, 'name', 'unknown')}: {str(e)}")
        
        try:
            # Process all top-level layers
            if hasattr(psd, 'layers') and psd.layers:
                for layer in psd.layers:
                    process_layer(layer)
            else:
                logger.warning("PSD file has no layers")
        except Exception as e:
            logger.error(f"Error processing PSD layers: {str(e)}")
        
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
