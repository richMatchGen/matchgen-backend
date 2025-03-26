from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.conf import settings

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, username=None,**extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username,**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)
    
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    profile_picture = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
    
class Club(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clubs"
    )
    name = models.CharField(max_length=100)
    logo = models.URLField(blank=True, null=True)
    sport = models.CharField(max_length=50)

    location = models.CharField(max_length=500, blank=True, null=True)
    founded_year = models.PositiveIntegerField(blank=True, null=True)
    venue_name = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    primary_color = models.CharField(max_length=7, blank=True, null=True)
    secondary_color = models.CharField(max_length=7, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    league = models.CharField(max_length=100, blank=True, null=True)


    def __str__(self):
        return self.name    