from django.urls import path
from .views import FeedbackSubmissionView, FeedbackListView, FeedbackStatsView

urlpatterns = [
    path('submit/', FeedbackSubmissionView.as_view(), name='feedback-submit'),
    path('list/', FeedbackListView.as_view(), name='feedback-list'),
    path('stats/', FeedbackStatsView.as_view(), name='feedback-stats'),
]
