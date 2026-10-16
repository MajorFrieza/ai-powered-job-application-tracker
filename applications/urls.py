from django.urls import path

from .views import (
    ApplicationAnalyzeView,
    ApplicationDetailView,
    ApplicationListCreateView,
    ApplicationStatusUpdateView,
)

urlpatterns = [
    path('applications/', ApplicationListCreateView.as_view(), name='application-list'),
    path('applications/<str:application_id>/analyze/', ApplicationAnalyzeView.as_view(), name='application-analyze'),
    path('applications/<str:application_id>/status/', ApplicationStatusUpdateView.as_view(), name='application-status'),
    path('applications/<str:application_id>/', ApplicationDetailView.as_view(), name='application-detail'),
]
