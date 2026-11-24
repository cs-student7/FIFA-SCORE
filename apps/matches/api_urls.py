from django.urls import path
from . import api_views
from .api_views import (
    MatchDetailAPIView,
    MatchEventsAPIView,
    MatchListAPIView,
    MatchMomentumAPIView,
    MatchStatsAPIView,
    live_matches,
    match_events,
    match_lineups,
    match_notifications,
    match_stats,
    wc_all_data,
    wc_live_scores,
)

urlpatterns = [
    path('notifications/', match_notifications, name='match-notifications'),
    path('live/', live_matches, name='live-matches'),
    path('wc/live/', wc_live_scores, name='wc-live'),
    path('wc/all/', wc_all_data, name='wc-all'),
    path('<int:fixture_id>/full-center/', api_views.fixture_full_center_api, name='api-fixture-full-center'),
    path('<int:fixture_id>/match-events/', match_events, name='match-events-api'),
    path('<int:fixture_id>/lineups/', match_lineups, name='match-lineups-api'),
    path('<int:fixture_id>/match-stats/', match_stats, name='match-stats-api'),
    path('<int:pk>/stats/', MatchStatsAPIView.as_view(), name='match-stats'),
    path('<int:pk>/momentum/', MatchMomentumAPIView.as_view(), name='match-momentum'),
    path('<int:pk>/events/', MatchEventsAPIView.as_view(), name='match-events'),
    path('<int:pk>/', MatchDetailAPIView.as_view(), name='api-match-detail'),
    path('', MatchListAPIView.as_view(), name='api-match-list'),
]
