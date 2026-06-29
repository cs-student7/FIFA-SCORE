# apps/matches/api_urls.py
from django.urls import path
from .api_views import wc_live_scores, wc_all_data
from .api_views import live_matches, match_events, match_lineups, match_stats
from . import api_views
from .api_views import (
    LiveMatchesAPIView, MatchListAPIView, MatchDetailAPIView,
    MatchStatsAPIView, MatchMomentumAPIView, MatchEventsAPIView,
    live_matches, match_events, match_lineups, match_stats,
)

urlpatterns = [
    # DB-based views
    path('', MatchListAPIView.as_view(), name='api-match-list'),
    path('<int:pk>/', MatchDetailAPIView.as_view(), name='api-match-detail'),
    path('<int:pk>/stats/', MatchStatsAPIView.as_view(), name='match-stats'),
    path('<int:pk>/momentum/', MatchMomentumAPIView.as_view(), name='match-momentum'),
    path('<int:pk>/events/', MatchEventsAPIView.as_view(), name='match-events'),

    # football-data.org live API proxy views
    path('live/', live_matches, name='live-matches'),
    path('<int:fixture_id>/match-events/', match_events, name='match-events-api'),
    path('<int:fixture_id>/lineups/', match_lineups, name='match-lineups-api'),
    path('<int:fixture_id>/match-stats/', match_stats, name='match-stats-api'),
    path('live/', live_matches, name='live-matches'),
    path('wc/live/', api_views.wc_live, name='wc-live'),
    path('wc/live/',    wc_live_scores, name='wc-live'),
    path('wc/all/',     wc_all_data,    name='wc-all'),
    path('wc/live/', wc_live_scores, name='wc-live'),
    path('wc/all/',  wc_all_data,    name='wc-all'),
    
]