from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from users.models import Club, User
from django.conf import settings

# Create your models here.
class GraphicPack(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    preview_image = models.ImageField(upload_to='graphic_packs/previews/')
    zip_file = models.FileField(upload_to='graphic_packs/files/')  # optional

class UserSelection(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    selected_pack = models.ForeignKey(GraphicPack, on_delete=models.SET_NULL, null=True)