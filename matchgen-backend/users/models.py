from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from graphicpack.models import GraphicPack


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, username=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    profile_picture = models.URLField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Email verification fields
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Club(models.Model):
    SUBSCRIPTION_TIERS = [
        ('basic', 'Basic Gen'),
        ('semipro', 'SemiPro Gen'),
        ('prem', 'Prem Gen'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="clubs"
    )
    name = models.CharField(max_length=100)
    logo = models.URLField(max_length=500, blank=True, null=True)
    sport = models.CharField(max_length=50)

    location = models.CharField(max_length=500, blank=True, null=True)
    founded_year = models.PositiveIntegerField(blank=True, null=True)
    venue_name = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(max_length=500, blank=True, null=True)
    primary_color = models.CharField(max_length=7, blank=True, null=True)
    secondary_color = models.CharField(max_length=7, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    league = models.CharField(max_length=100, blank=True, null=True)
    selected_pack = models.ForeignKey(
        GraphicPack, on_delete=models.SET_NULL, null=True, blank=True
    )
    
    # Subscription fields
    subscription_tier = models.CharField(
        max_length=20, 
        choices=SUBSCRIPTION_TIERS, 
        null=True,
        blank=True
    )
    subscription_active = models.BooleanField(default=False)
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(blank=True, null=True)
    subscription_canceled = models.BooleanField(default=False)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    
    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.get_name_display()


class ClubMembership(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='club_memberships')
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='memberships')
    role = models.ForeignKey(UserRole, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invited_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sent_invites'
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        unique_together = ('user', 'club')
    
    def __str__(self):
        return f"{self.user.email} - {self.club.name} ({self.role.name})"


class Feature(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)  # e.g., 'post.matchday', 'post.result'
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name


class SubscriptionTierFeature(models.Model):
    subscription_tier = models.CharField(max_length=20, choices=Club.SUBSCRIPTION_TIERS)
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('subscription_tier', 'feature')
    
    def __str__(self):
        return f"{self.subscription_tier} - {self.feature.name}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('invite_sent', 'Invite Sent'),
        ('invite_accepted', 'Invite Accepted'),
        ('role_changed', 'Role Changed'),
        ('role_revoked', 'Role Revoked'),
        ('feature_access', 'Feature Access'),
        ('subscription_changed', 'Subscription Changed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.timestamp}"
