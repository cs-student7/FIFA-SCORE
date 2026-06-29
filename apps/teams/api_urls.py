from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.TeamListAPIView.as_view(), name='api-team-list'),
    path('<int:pk>/', api_views.TeamDetailAPIView.as_view(), name='api-team-detail'),
]
