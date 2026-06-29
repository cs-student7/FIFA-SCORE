from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.CompetitionListAPIView.as_view(), name='api-competition-list'),
    path('<int:pk>/', api_views.CompetitionDetailAPIView.as_view(), name='api-competition-detail'),
    path('standings/<int:season_id>/', api_views.StandingsAPIView.as_view(), name='api-standings'),
    path('top-scorers/<int:season_id>/', api_views.TopScorersAPIView.as_view(), name='api-top-scorers'),
]
