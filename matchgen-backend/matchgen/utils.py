"""
Utility functions for the MatchGen project.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from django.http import Http404
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent API error responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the error response format
        error_data = {
            'error': True,
            'message': response.data.get('detail', str(exc)),
            'code': response.status_code,
        }
        
        # Add field-specific errors if they exist
        if isinstance(response.data, dict) and 'detail' not in response.data:
            error_data['fields'] = response.data
        
        response.data = error_data
        return response
    
    # Handle Django-specific exceptions
    if isinstance(exc, ValidationError):
        error_data = {
            'error': True,
            'message': 'Validation error',
            'code': status.HTTP_400_BAD_REQUEST,
            'fields': exc.message_dict if hasattr(exc, 'message_dict') else {'detail': str(exc)}
        }
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
    
    if isinstance(exc, Http404):
        error_data = {
            'error': True,
            'message': 'Resource not found',
            'code': status.HTTP_404_NOT_FOUND,
        }
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)
    
    # Log unexpected exceptions
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    # Return a generic error response for unexpected exceptions
    error_data = {
        'error': True,
        'message': 'An unexpected error occurred',
        'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def validate_email(email):
    """
    Validate email format.
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password):
    """
    Validate password strength.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is strong"


def sanitize_filename(filename):
    """
    Sanitize filename for safe storage.
    """
    import re
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1)
        filename = name[:255-len(ext)-1] + '.' + ext
    return filename


def format_file_size(size_bytes):
    """
    Format file size in human readable format.
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"
