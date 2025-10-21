from django.db import models
from django.conf import settings


class Feedback(models.Model):
    """Model to store user feedback and suggestions."""
    
    FEEDBACK_TYPES = [
        ('general', 'General Feedback'),
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('support', 'Technical Support'),
        ('billing', 'Billing Question'),
    ]
    
    RATING_CHOICES = [
        (1, 'Very Poor'),
        (2, 'Poor'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]
    
    # User information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedback_submissions'
    )
    name = models.CharField(max_length=255, help_text="User's name")
    email = models.EmailField(help_text="User's email address")
    
    # Feedback content
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_TYPES,
        default='general',
        help_text="Type of feedback"
    )
    subject = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Brief subject line"
    )
    message = models.TextField(help_text="Detailed feedback message")
    
    # Rating and preferences
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        default=5,
        help_text="User's rating of the service"
    )
    allow_contact = models.BooleanField(
        default=True,
        help_text="Whether user allows follow-up contact"
    )
    subscribe_newsletter = models.BooleanField(
        default=False,
        help_text="Whether user wants to subscribe to newsletter"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New'),
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved'),
            ('closed', 'Closed'),
        ],
        default='new',
        help_text="Current status of the feedback"
    )
    priority = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        default='medium',
        help_text="Priority level of the feedback"
    )
    
    # Admin response
    admin_response = models.TextField(
        blank=True,
        null=True,
        help_text="Response from admin team"
    )
    admin_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes for admin team"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['feedback_type']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_feedback_type_display()} from {self.name} ({self.created_at.strftime('%Y-%m-%d')})"
    
    @property
    def is_urgent(self):
        """Check if feedback is urgent based on type and priority."""
        return (
            self.priority == 'urgent' or
            (self.feedback_type == 'bug' and self.priority == 'high') or
            (self.feedback_type == 'support' and self.priority in ['high', 'urgent'])
        )
    
    @property
    def days_since_creation(self):
        """Get number of days since feedback was created."""
        from django.utils import timezone
        return (timezone.now() - self.created_at).days





