import logging
from django.utils import timezone
from django.db import models
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.mail import send_mail
from django.conf import settings
from .models import Feedback
from .serializers import FeedbackSerializer, FeedbackSubmissionSerializer

logger = logging.getLogger(__name__)


class FeedbackSubmissionView(APIView):
    """Handle feedback submission from users."""
    permission_classes = [AllowAny]  # Allow anonymous feedback
    
    def post(self, request):
        """Submit new feedback."""
        try:
            # Get user from request if authenticated
            user = request.user if request.user.is_authenticated else None
            
            # Prepare data for serializer
            data = request.data.copy()
            if user:
                data['user'] = user.id
                # Pre-fill name and email if not provided
                if not data.get('name') and user.first_name:
                    data['name'] = f"{user.first_name} {user.last_name}".strip()
                if not data.get('email') and user.email:
                    data['email'] = user.email
            
            # Validate and create feedback
            serializer = FeedbackSubmissionSerializer(data=data)
            if serializer.is_valid():
                feedback = serializer.save(user=user)
                
                # Set priority based on feedback type
                if feedback.feedback_type == 'bug':
                    feedback.priority = 'high'
                elif feedback.feedback_type == 'support':
                    feedback.priority = 'medium'
                elif feedback.feedback_type == 'feature':
                    feedback.priority = 'low'
                else:
                    feedback.priority = 'medium'
                
                feedback.save()
                
                # Send notification email to admin
                try:
                    self._send_admin_notification(feedback)
                except Exception as email_error:
                    logger.warning(f"Failed to send admin notification email: {str(email_error)}")
                
                # Send confirmation email to user
                try:
                    self._send_user_confirmation(feedback)
                except Exception as email_error:
                    logger.warning(f"Failed to send user confirmation email: {str(email_error)}")
                
                logger.info(f"Feedback submitted: {feedback.id} from {feedback.email}")
                
                return Response({
                    "message": "Thank you for your feedback! We'll get back to you soon.",
                    "feedback_id": feedback.id,
                    "status": "submitted"
                }, status=status.HTTP_201_CREATED)
            
            else:
                return Response({
                    "error": "Invalid feedback data",
                    "details": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}", exc_info=True)
            return Response({
                "error": "An error occurred while submitting your feedback. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _send_admin_notification(self, feedback):
        """Send notification email to admin team."""
        subject = f"New {feedback.get_feedback_type_display()}: {feedback.subject or 'No Subject'}"
        
        message = f"""
New feedback has been submitted:

Type: {feedback.get_feedback_type_display()}
From: {feedback.name} ({feedback.email})
Rating: {feedback.rating}/5
Priority: {feedback.get_priority_display()}

Subject: {feedback.subject or 'No subject'}

Message:
{feedback.message}

Submitted: {feedback.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Allow Contact: {'Yes' if feedback.allow_contact else 'No'}
Subscribe Newsletter: {'Yes' if feedback.subscribe_newsletter else 'No'}

You can view and respond to this feedback in the admin panel.
        """.strip()
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL] if hasattr(settings, 'ADMIN_EMAIL') else ['admin@matchgen.com'],
            fail_silently=True
        )
    
    def _send_user_confirmation(self, feedback):
        """Send confirmation email to user."""
        subject = "Thank you for your feedback - MatchGen"
        
        message = f"""
Hi {feedback.name},

Thank you for taking the time to provide feedback about MatchGen. We've received your {feedback.get_feedback_type_display().lower()} and will review it carefully.

Your feedback details:
- Type: {feedback.get_feedback_type_display()}
- Subject: {feedback.subject or 'No subject'}
- Rating: {feedback.rating}/5

We typically respond within 24 hours during business days. If you have any urgent questions, please don't hesitate to contact us directly.

Best regards,
The MatchGen Team
        """.strip()
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[feedback.email],
            fail_silently=True
        )


class FeedbackListView(APIView):
    """List feedback for authenticated users (their own feedback)."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's feedback submissions."""
        try:
            feedback_list = Feedback.objects.filter(user=request.user).order_by('-created_at')
            serializer = FeedbackSerializer(feedback_list, many=True)
            
            return Response({
                "feedback": serializer.data,
                "count": feedback_list.count()
            })
            
        except Exception as e:
            logger.error(f"Error fetching user feedback: {str(e)}", exc_info=True)
            return Response({
                "error": "An error occurred while fetching your feedback."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FeedbackStatsView(APIView):
    """Get feedback statistics (admin only)."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get feedback statistics."""
        try:
            # Check if user is admin (you might want to add proper admin permission check)
            if not request.user.is_staff:
                return Response({
                    "error": "Permission denied"
                }, status=status.HTTP_403_FORBIDDEN)
            
            total_feedback = Feedback.objects.count()
            new_feedback = Feedback.objects.filter(status='new').count()
            in_progress = Feedback.objects.filter(status='in_progress').count()
            resolved = Feedback.objects.filter(status='resolved').count()
            
            # Average rating
            avg_rating = Feedback.objects.aggregate(
                avg_rating=models.Avg('rating')
            )['avg_rating'] or 0
            
            # Feedback by type
            by_type = {}
            for feedback_type, _ in Feedback.FEEDBACK_TYPES:
                count = Feedback.objects.filter(feedback_type=feedback_type).count()
                if count > 0:
                    by_type[feedback_type] = count
            
            # Recent feedback (last 30 days)
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_feedback = Feedback.objects.filter(created_at__gte=thirty_days_ago).count()
            
            return Response({
                "total_feedback": total_feedback,
                "new_feedback": new_feedback,
                "in_progress": in_progress,
                "resolved": resolved,
                "average_rating": round(avg_rating, 2),
                "by_type": by_type,
                "recent_feedback": recent_feedback
            })
            
        except Exception as e:
            logger.error(f"Error fetching feedback stats: {str(e)}", exc_info=True)
            return Response({
                "error": "An error occurred while fetching feedback statistics."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
