from rest_framework import serializers
from .models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer for Feedback model."""
    
    # Computed fields
    days_since_creation = serializers.ReadOnlyField()
    is_urgent = serializers.ReadOnlyField()
    
    class Meta:
        model = Feedback
        fields = [
            'id', 'user', 'name', 'email', 'feedback_type', 'subject', 'message',
            'rating', 'allow_contact', 'subscribe_newsletter', 'status', 'priority',
            'admin_response', 'admin_notes', 'created_at', 'updated_at', 'responded_at',
            'days_since_creation', 'is_urgent'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'priority', 'admin_response', 'admin_notes',
            'created_at', 'updated_at', 'responded_at', 'days_since_creation', 'is_urgent'
        ]
    
    def validate_message(self, value):
        """Validate message is not empty and has reasonable length."""
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message should be at least 10 characters long.")
        
        if len(value) > 5000:
            raise serializers.ValidationError("Message is too long. Please keep it under 5000 characters.")
        
        return value.strip()
    
    def validate_subject(self, value):
        """Validate subject if provided."""
        if value and len(value) > 255:
            raise serializers.ValidationError("Subject is too long. Please keep it under 255 characters.")
        return value
    
    def validate_rating(self, value):
        """Validate rating is within valid range."""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class FeedbackSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for feedback submission (user-facing)."""
    
    class Meta:
        model = Feedback
        fields = [
            'name', 'email', 'feedback_type', 'subject', 'message',
            'rating', 'allow_contact', 'subscribe_newsletter'
        ]
    
    def validate_message(self, value):
        """Validate message is not empty and has reasonable length."""
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message should be at least 10 characters long.")
        
        if len(value) > 5000:
            raise serializers.ValidationError("Message is too long. Please keep it under 5000 characters.")
        
        return value.strip()
    
    def validate_subject(self, value):
        """Validate subject if provided."""
        if value and len(value) > 255:
            raise serializers.ValidationError("Subject is too long. Please keep it under 255 characters.")
        return value
    
    def validate_rating(self, value):
        """Validate rating is within valid range."""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value









