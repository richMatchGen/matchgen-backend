import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth import get_user_model
from django.db import connection

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomJWTAuthentication(JWTAuthentication):
    """Custom JWT authentication that handles missing database fields gracefully."""
    
    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        Handles missing email verification fields gracefully.
        """
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
            return user
        except Exception as e:
            # Handle case where email verification fields don't exist
            logger.warning(f"Database fields not available during JWT auth: {str(e)}")
            
            try:
                # Get user_id from token
                user_id = validated_token[api_settings.USER_ID_CLAIM]
                
                # Try to get user with raw SQL
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, email, username, profile_picture, is_active, is_staff, is_superuser, password FROM users_user WHERE id = %s",
                        [user_id]
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        user = User()
                        user.id = row[0]
                        user.email = row[1]
                        user.username = row[2]
                        user.profile_picture = row[3]
                        user.is_active = row[4]
                        user.is_staff = row[5]
                        user.is_superuser = row[6]
                        user.password = row[7]
                        
                        # Set email_verified to True for existing users
                        if hasattr(user, 'email_verified'):
                            user.email_verified = True
                        
                        return user
                    else:
                        raise InvalidToken('User not found')
                        
            except Exception as sql_error:
                logger.error(f"Failed to get user with raw SQL: {str(sql_error)}")
                raise InvalidToken('User not found')
