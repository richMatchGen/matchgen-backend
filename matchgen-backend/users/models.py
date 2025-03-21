from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    """Custom user model manager where email is the unique identifier for authentication"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Custom User model that uses email as the primary login field"""
    username = None  # Remove username field
    email = models.EmailField(unique=True)  # Make email unique

    USERNAME_FIELD = "email"  # Use email for authentication
    REQUIRED_FIELDS = []  # No username required

    objects = UserManager()

    def __str__(self):
        return self.email