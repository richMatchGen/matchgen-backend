# PSD Processor

A Django application for processing PSD (Photoshop) files and extracting layer information including bounding boxes, positions, and dimensions.

## Features

- Upload PSD files and automatically extract layer information
- Extract bounding box coordinates (x, y, width, height) for each layer
- Support for nested layer groups
- Store layer metadata (visibility, opacity, layer type)
- RESTful API endpoints for integration
- User authentication and file ownership
- Clean file management (automatic cleanup after processing)

## API Endpoints

### Upload PSD File
```
POST /api/psd/upload/
Content-Type: multipart/form-data
Authorization: Bearer <token>

Parameters:
- file: PSD file
- title: Document title
```

### List User's PSD Documents
```
GET /api/psd/documents/
Authorization: Bearer <token>
```

### Get PSD Document Details
```
GET /api/psd/documents/{id}/
Authorization: Bearer <token>
```

### Get Document Layers
```
GET /api/psd/documents/{id}/layers/
Authorization: Bearer <token>
```

### Delete PSD Document
```
DELETE /api/psd/documents/{id}/delete/
Authorization: Bearer <token>
```

## Models

### PSDDocument
- `user`: Foreign key to User model
- `title`: Document title
- `file`: File path (stored temporarily)
- `uploaded_at`: Upload timestamp
- `width`: Document width in pixels
- `height`: Document height in pixels

### PSDLayer
- `document`: Foreign key to PSDDocument
- `name`: Layer name (including group hierarchy)
- `x`, `y`: Layer position coordinates
- `width`, `height`: Layer dimensions
- `visible`: Layer visibility status
- `opacity`: Layer opacity (0-100%)
- `layer_type`: Type of layer (layer/group)

## Frontend Integration

The PSD processor includes a React frontend component (`PSDProcessor.jsx`) that provides:

- File upload interface with drag-and-drop support
- Document management table
- Layer information display in a detailed table
- Real-time processing status
- Error handling and user feedback

## Installation

1. Install required packages:
```bash
pip install psd-tools
```

2. Add to Django settings:
```python
INSTALLED_APPS = [
    # ... other apps
    'psd_processor',
]
```

3. Run migrations:
```bash
python manage.py makemigrations psd_processor
python manage.py migrate
```

4. Add URL patterns:
```python
urlpatterns = [
    # ... other patterns
    path('api/psd/', include('psd_processor.urls')),
]
```

## Usage Example

### Backend Processing
```python
from psd_tools import PSDImage

# Open PSD file
psd = PSDImage.open('example.psd')

# Extract layer information
for layer in psd.layers:
    if hasattr(layer, 'bbox') and layer.bbox:
        bbox = layer.bbox
        print(f"Layer: {layer.name}")
        print(f"Position: ({bbox[0]}, {bbox[1]})")
        print(f"Size: {bbox[2] - bbox[0]} x {bbox[3] - bbox[1]}")
```

### Frontend Usage
Navigate to `/psd-processor` in your application to access the PSD processing interface.

## File Processing Flow

1. User uploads PSD file via frontend
2. File is temporarily stored
3. `psd-tools` library processes the file
4. Layer information is extracted recursively
5. Data is stored in database
6. Temporary file is cleaned up
7. Processed data is returned to user

## Security Features

- User authentication required for all operations
- File ownership validation
- File type validation (PSD only)
- Automatic file cleanup after processing
- No persistent storage of uploaded files

## Error Handling

- Invalid file type validation
- PSD parsing error handling
- Database error handling
- User permission validation
- File size and format validation

## Dependencies

- `psd-tools`: Core PSD processing library
- `Pillow`: Image processing support
- `Django REST Framework`: API functionality
- `Django`: Web framework








