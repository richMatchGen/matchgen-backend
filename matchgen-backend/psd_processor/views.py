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
from graphicpack.models import GraphicPack, TextElement

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
                
                # Log PSD structure for debugging
                logger.info(f"PSD object type: {type(psd)}")
                logger.info(f"PSD attributes: {[attr for attr in dir(psd) if not attr.startswith('_')]}")
                
                # Check for layers attribute
                if hasattr(psd, 'layers'):
                    logger.info(f"PSD has layers attribute: {psd.layers}")
                    if psd.layers:
                        logger.info(f"Number of layers: {len(psd.layers)}")
                        for i, layer in enumerate(psd.layers):
                            logger.info(f"Layer {i}: {getattr(layer, 'name', 'unnamed')} - {type(layer)}")
                    else:
                        logger.warning("PSD layers attribute is empty")
                else:
                    logger.warning("PSD object does not have layers attribute")
                    
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
                layer_name = getattr(layer, 'name', 'unnamed')
                logger.debug(f"Processing layer: {layer_name}, type: {type(layer)}")
                
                # Log all available attributes for debugging
                if logger.isEnabledFor(logging.DEBUG):
                    attrs = [attr for attr in dir(layer) if not attr.startswith('_')]
                    logger.debug(f"Layer {layer_name} attributes: {attrs}")
                
                if hasattr(layer, 'layers') and layer.layers:
                    # This is a group
                    logger.debug(f"Layer {layer_name} is a group with {len(layer.layers)} sub-layers")
                    for sub_layer in layer.layers:
                        process_layer(sub_layer, f"{parent_name}{layer_name}/" if parent_name else f"{layer_name}/")
                else:
                    # This is a regular layer
                    full_layer_name = f"{parent_name}{layer_name}" if parent_name else layer_name
                    logger.debug(f"Processing regular layer: {full_layer_name}")
                    
                    # Get bounding box safely - try multiple methods
                    bbox = None
                    bbox_method = None
                    
                    # Method 1: Standard bbox attribute
                    if hasattr(layer, 'bbox') and layer.bbox:
                        bbox = layer.bbox
                        bbox_method = "bbox"
                    # Method 2: Individual coordinate attributes
                    elif hasattr(layer, 'left') and hasattr(layer, 'top') and hasattr(layer, 'right') and hasattr(layer, 'bottom'):
                        bbox = (layer.left, layer.top, layer.right, layer.bottom)
                        bbox_method = "individual_coords"
                    # Method 3: Try to get coordinates from different attributes
                    elif hasattr(layer, 'x') and hasattr(layer, 'y') and hasattr(layer, 'width') and hasattr(layer, 'height'):
                        bbox = (layer.x, layer.y, layer.x + layer.width, layer.y + layer.height)
                        bbox_method = "x_y_width_height"
                    # Method 4: Try to access through layer record
                    elif hasattr(layer, 'layer_record'):
                        layer_record = layer.layer_record
                        if hasattr(layer_record, 'left') and hasattr(layer_record, 'top') and hasattr(layer_record, 'right') and hasattr(layer_record, 'bottom'):
                            bbox = (layer_record.left, layer_record.top, layer_record.right, layer_record.bottom)
                            bbox_method = "layer_record"
                    
                    logger.debug(f"Bounding box method: {bbox_method}, bbox: {bbox}")
                    
                    if bbox and len(bbox) >= 4:
                        # Calculate dimensions
                        x = int(bbox[0]) if bbox[0] is not None else 0
                        y = int(bbox[1]) if bbox[1] is not None else 0
                        width = int(bbox[2] - bbox[0]) if bbox[2] is not None and bbox[0] is not None else 0
                        height = int(bbox[3] - bbox[1]) if bbox[3] is not None and bbox[1] is not None else 0
                        
                        # Calculate center points
                        center_x = x + (width / 2.0)
                        center_y = y + (height / 2.0)
                        
                        # Get visibility and opacity safely
                        visible = getattr(layer, 'visible', True)
                        opacity = getattr(layer, 'opacity', 1.0)
                        if isinstance(opacity, (int, float)) and opacity <= 1.0:
                            opacity = opacity * 100
                        
                        layer_data = {
                            'name': full_layer_name,
                            'x': x,
                            'y': y,
                            'width': width,
                            'height': height,
                            'center_x': center_x,
                            'center_y': center_y,
                            'visible': bool(visible),
                            'opacity': float(opacity),
                            'layer_type': 'group' if hasattr(layer, 'layers') and layer.layers else 'layer'
                        }
                        layers_data.append(layer_data)
                        logger.info(f"Successfully extracted layer: {full_layer_name} at ({x}, {y}) - {width}x{height}, center=({center_x:.1f}, {center_y:.1f})")
                    else:
                        logger.warning(f"Could not extract bounding box for layer: {full_layer_name}. Available attributes: {[attr for attr in dir(layer) if not attr.startswith('_')]}")
                        
                        # Create a basic layer entry even without bounding box
                    layer_data = {
                            'name': full_layer_name,
                            'x': 0,
                            'y': 0,
                            'width': 0,
                            'height': 0,
                            'center_x': 0.0,
                            'center_y': 0.0,
                            'visible': getattr(layer, 'visible', True),
                            'opacity': float(getattr(layer, 'opacity', 1.0)) * 100 if getattr(layer, 'opacity', 1.0) <= 1.0 else float(getattr(layer, 'opacity', 100.0)),
                            'layer_type': 'layer'
                    }
                    layers_data.append(layer_data)
                    logger.info(f"Created basic layer entry for: {full_layer_name}")
                        
            except Exception as e:
                logger.error(f"Error processing layer {getattr(layer, 'name', 'unknown')}: {str(e)}", exc_info=True)
        
        try:
            # Process all top-level layers
            if hasattr(psd, 'layers') and psd.layers:
                logger.info(f"Found {len(psd.layers)} top-level layers")
                for i, layer in enumerate(psd.layers):
                    logger.debug(f"Processing layer {i}: {getattr(layer, 'name', 'unnamed')}")
                    process_layer(layer)
            else:
                logger.warning("PSD file has no layers attribute or empty layers")
                
            # Try alternative layer access methods
            if not layers_data:
                logger.info("No layers found with standard method, trying alternative approaches...")
                
                # Try accessing layers through different attributes
                for attr_name in ['_layers', 'layer_and_mask', 'layers_and_masks']:
                    if hasattr(psd, attr_name):
                        attr_value = getattr(psd, attr_name)
                        logger.info(f"Found attribute {attr_name}: {type(attr_value)}")
                        
                        # Handle direct list of layers
                        if isinstance(attr_value, list):
                            logger.info(f"Found {len(attr_value)} layers in {attr_name} (list)")
                            for i, layer in enumerate(attr_value):
                                logger.debug(f"Processing layer {i} from {attr_name}: {getattr(layer, 'name', 'unnamed')}")
                                process_layer(layer)
                            if attr_value:  # If we found layers, break
                                break
                        # Handle object with layers attribute
                        elif hasattr(attr_value, 'layers') and attr_value.layers:
                            logger.info(f"Found {len(attr_value.layers)} layers in {attr_name}")
                            for i, layer in enumerate(attr_value.layers):
                                logger.debug(f"Processing layer {i} from {attr_name}: {getattr(layer, 'name', 'unnamed')}")
                                process_layer(layer)
                            break
                
                # Try to access layer information directly from the PSD structure
                if not layers_data and hasattr(psd, '_psd'):
                    logger.info("Trying to access layers through _psd attribute...")
                    try:
                        psd_obj = psd._psd
                        logger.info(f"_psd object type: {type(psd_obj)}")
                        logger.info(f"_psd attributes: {[attr for attr in dir(psd_obj) if not attr.startswith('_')]}")
                        
                        if hasattr(psd_obj, 'layer_and_mask_information'):
                            layer_info = psd_obj.layer_and_mask_information
                            logger.info(f"layer_and_mask_information type: {type(layer_info)}")
                            logger.info(f"layer_and_mask_information attributes: {[attr for attr in dir(layer_info) if not attr.startswith('_')]}")
                            
                            if hasattr(layer_info, 'layer_info') and hasattr(layer_info.layer_info, 'layers'):
                                layers = layer_info.layer_info.layers
                                logger.info(f"Found {len(layers)} layers in layer_info")
                                for i, layer in enumerate(layers):
                                    logger.debug(f"Processing layer {i} from layer_info: {getattr(layer, 'name', 'unnamed')}")
                                    process_layer(layer)
                            else:
                                logger.warning("No layer_info.layers found")
                        else:
                            logger.warning("No layer_and_mask_information found")
                    except Exception as e:
                        logger.error(f"Error accessing layers through _psd: {str(e)}")
                
                # Try alternative methods to find layers
                if not layers_data:
                    logger.info("Trying additional layer detection methods...")
                    
                    # Try to iterate through the PSD object itself
                    try:
                        logger.info("Attempting to iterate through PSD object...")
                        for i, item in enumerate(psd):
                            logger.info(f"PSD item {i}: {type(item)} - {getattr(item, 'name', 'unnamed')}")
                            process_layer(item)
                    except Exception as e:
                        logger.debug(f"Could not iterate through PSD object: {str(e)}")
                    
                    # Try to access through descendants
                    if hasattr(psd, 'descendants'):
                        try:
                            descendants = psd.descendants
                            logger.info(f"Found {len(descendants)} descendants")
                            for i, descendant in enumerate(descendants):
                                logger.info(f"Descendant {i}: {type(descendant)} - {getattr(descendant, 'name', 'unnamed')}")
                                process_layer(descendant)
                        except Exception as e:
                            logger.error(f"Error accessing descendants: {str(e)}")
                    
                    # Try to find layers using the find method
                    if hasattr(psd, 'findall'):
                        try:
                            found_layers = psd.findall()
                            logger.info(f"Found {len(found_layers)} items using findall")
                            for i, layer in enumerate(found_layers):
                                logger.info(f"Found item {i}: {type(layer)} - {getattr(layer, 'name', 'unnamed')}")
                                process_layer(layer)
                        except Exception as e:
                            logger.error(f"Error using findall: {str(e)}")
                        
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


class PSDLayerProcessView(APIView):
    """Process selected layers and save them to both PSDLayer and TextElement models."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Process selected layers and create text elements."""
        try:
            document_id = request.data.get('document_id')
            graphic_pack_id = request.data.get('graphic_pack_id')
            content_type = request.data.get('content_type')
            layer_names = request.data.get('layer_names', [])
            
            if not all([document_id, graphic_pack_id, content_type, layer_names]):
                return Response(
                    {'error': 'Missing required fields: document_id, graphic_pack_id, content_type, layer_names'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the PSD document
            try:
                document = PSDDocument.objects.get(id=document_id, user=request.user)
            except PSDDocument.DoesNotExist:
                return Response(
                    {'error': 'PSD document not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get the graphic pack
            try:
                graphic_pack = GraphicPack.objects.get(id=graphic_pack_id)
            except GraphicPack.DoesNotExist:
                return Response(
                    {'error': 'Graphic pack not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get layers that match the selected names
            matching_layers = document.layers.filter(name__in=layer_names)
            
            if not matching_layers.exists():
                return Response(
                    {'error': 'No layers found matching the selected names'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            created_text_elements = []
            
            for layer in matching_layers:
                # Log layer positioning information
                logger.info(f"Processing layer {layer.name}: top-left=({layer.x}, {layer.y}), center=({layer.center_x:.1f}, {layer.center_y:.1f}), size={layer.width}x{layer.height}")
                
                # Determine element type based on layer name
                element_type = 'image' if layer.name in ['club_logo', 'opponent_logo', 'player_image', 'photo_image'] else 'text'
                
                # Determine alignment based on content type
                alignment = 'left' if content_type == 'startingXI' else 'center'
                
                # Calculate position based on anchor point
                # Text elements: top-center anchor (position_y = top of layer)
                # Image elements: center-center anchor (position = center of layer)
                if element_type == 'text':
                    # For text elements, use top-center positioning
                    position_x = int(layer.center_x)  # Center X
                    position_y = int(layer.y)  # Top Y (not center)
                    logger.info(f"Text element {layer.name}: using top-center positioning ({position_x}, {position_y})")
                else:
                    # For image elements, use center-center positioning
                    position_x = int(layer.center_x)  # Center X
                    position_y = int(layer.center_y)  # Center Y
                    logger.info(f"Image element {layer.name}: using center-center positioning ({position_x}, {position_y})")
                
                # Create TextElement with calculated positions
                text_element_data = {
                    'graphic_pack': graphic_pack,
                    'content_type': content_type,
                    'element_name': layer.name,
                    'element_type': element_type,
                    'position_x': position_x,
                    'position_y': position_y,
                    'font_size': 48,
                    'font_family': 'Montserrat',
                    'font_color': '#FFFFFF',
                    'alignment': alignment,
                    'font_weight': 'normal',
                    'maintain_aspect_ratio': True,
                    'image_color_tint': '#FFFFFF'
                }
                
                # Set image dimensions for image elements
                if element_type == 'image':
                    text_element_data.update({
                        'image_width': 200,
                        'image_height': 200
                    })
                
                # Set home/away positions for specific logos using anchor-based coordinates
                # Club logo uses opponent position for away games
                # Opponent logo uses club position for home games
                if layer.name == 'club_logo':
                    # Club logo is an image element, use center-center positioning
                    text_element_data.update({
                        'away_position_x': int(layer.center_x),  # Center X
                        'away_position_y': int(layer.center_y)   # Center Y
                    })
                    logger.info(f"Set club_logo away position to center-center ({int(layer.center_x)}, {int(layer.center_y)})")
                elif layer.name == 'opponent_logo':
                    # Opponent logo is an image element, use center-center positioning
                    text_element_data.update({
                        'home_position_x': int(layer.center_x),  # Center X
                        'home_position_y': int(layer.center_y)   # Center Y
                    })
                    logger.info(f"Set opponent_logo home position to center-center ({int(layer.center_x)}, {int(layer.center_y)})")
                
                # Create the TextElement (handle unique constraint)
                try:
                    text_element = TextElement.objects.create(**text_element_data)
                    created_text_elements.append(text_element)
                except Exception as e:
                    logger.warning(f"Failed to create TextElement for layer {layer.name}: {str(e)}")
                    # Try to get existing element or create with unique name
                    try:
                        # Check if element already exists
                        existing_element = TextElement.objects.get(
                            graphic_pack=graphic_pack,
                            content_type=content_type,
                            element_name=layer.name
                        )
                        logger.info(f"TextElement already exists for {layer.name}, updating position with anchor-based coordinates")
                        
                        # Update positions based on anchor point
                        if element_type == 'text':
                            # Text elements: top-center anchor
                            existing_element.position_x = int(layer.center_x)  # Center X
                            existing_element.position_y = int(layer.y)  # Top Y
                            logger.info(f"Updated text element {layer.name} to top-center ({int(layer.center_x)}, {int(layer.y)})")
                        else:
                            # Image elements: center-center anchor
                            existing_element.position_x = int(layer.center_x)  # Center X
                            existing_element.position_y = int(layer.center_y)  # Center Y
                            logger.info(f"Updated image element {layer.name} to center-center ({int(layer.center_x)}, {int(layer.center_y)})")
                        
                        # Update home/away positions for logos (always center-center for images)
                        if layer.name == 'club_logo':
                            existing_element.away_position_x = int(layer.center_x)
                            existing_element.away_position_y = int(layer.center_y)
                            logger.info(f"Updated club_logo away position to center-center ({int(layer.center_x)}, {int(layer.center_y)})")
                        elif layer.name == 'opponent_logo':
                            existing_element.home_position_x = int(layer.center_x)
                            existing_element.home_position_y = int(layer.center_y)
                            logger.info(f"Updated opponent_logo home position to center-center ({int(layer.center_x)}, {int(layer.center_y)})")
                        
                        existing_element.save()
                        created_text_elements.append(existing_element)
                    except TextElement.DoesNotExist:
                        # Create with unique name by appending layer ID
                        text_element_data['element_name'] = f"{layer.name}_{layer.id}"
                        text_element = TextElement.objects.create(**text_element_data)
                        created_text_elements.append(text_element)
                
                # Update the PSDLayer with graphic pack and content type
                layer.graphic_pack = graphic_pack
                layer.content_type = content_type
                layer.save()
            
            return Response({
                'message': f'Successfully processed {len(created_text_elements)} layers',
                'created_elements': len(created_text_elements),
                'text_elements': [
                    {
                        'id': element.id,
                        'element_name': element.element_name,
                        'element_type': element.element_type,
                        'position_x': element.position_x,
                        'position_y': element.position_y
                    } for element in created_text_elements
                ]
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error processing layers: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to process layers: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
