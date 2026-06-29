from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.PlayerListAPIView.as_view(), name='api-player-list'),
    path('<int:pk>/', api_views.PlayerDetailAPIView.as_view(), name='api-player-detail'),
]
