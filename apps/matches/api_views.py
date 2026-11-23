from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Match, MatchStatistic, MatchMomentum, MatchEvent
from .serializers import (
    MatchListSerializer, MatchDetailSerializer,
    MatchStatisticSerializer, MatchMomentumSerializer, MatchEventSerializer,
)


class LiveMatchesAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        matches = Match.objects.filter(
            status__in=['live', 'ht', 'extra_time', 'penalties']
        ).select_related('home_team', 'away_team', 'season__competition').order_by('kickoff')
        return Response(MatchListSerializer(matches, many=True).data)


class MatchListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = MatchListSerializer
    ordering = ['kickoff']

    def get_queryset(self):
        qs = Match.objects.select_related('home_team', 'away_team', 'season__competition')
        date_str = self.request.GET.get('date')
        if date_str:
            from datetime import datetime
            try:
                d = datetime.strptime(date_str, '%Y-%m-%d').date()
                qs = qs.filter(kickoff__date=d)
            except ValueError:
                pass
        else:
            qs = qs.filter(kickoff__date=timezone.now().date())
        return qs.order_by('kickoff')


class MatchDetailAPIView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = MatchDetailSerializer
    queryset = Match.objects.select_related(
        'home_team', 'away_team', 'season__competition', 'statistics'
    ).prefetch_related('events__player', 'events__team', 'momentum_data')


class MatchStatsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        stats = get_object_or_404(MatchStatistic, match_id=pk)
        return Response(MatchStatisticSerializer(stats).data)


class MatchMomentumAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        data = MatchMomentum.objects.filter(match_id=pk).order_by('minute')
        return Response(MatchMomentumSerializer(data, many=True).data)


class MatchEventsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        get_object_or_404(Match, pk=pk)
        events = MatchEvent.objects.filter(match_id=pk).select_related(
            'player', 'assist_player', 'team'
        ).order_by('minute', 'extra_time')
        return Response(MatchEventSerializer(events, many=True).data)

from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.matches.football_api import (
    get_live_matches, get_match_events as get_match_events,
    get_match_lineups, get_match_stats, get_today_matches
)


@api_view(['GET'])
def live_matches(request):
    """Called every 30 seconds by goalpulse.js ticker."""
    try:
        data = get_live_matches()
        return Response(data)
    except Exception:
        return Response([], status=200)


@api_view(['GET'])
def match_events(request, fixture_id):
    """Goals, cards, subs — used on match detail page."""
    try:
        return Response(get_match_events(fixture_id))
    except Exception as e:
        return Response({"error": str(e)}, status=503)


@api_view(['GET'])
def match_lineups(request, fixture_id):
    try:
        return Response(get_match_lineups(fixture_id))
    except Exception as e:
        return Response({"error": str(e)}, status=503)


@api_view(['GET'])
def match_stats(request, fixture_id):
    try:
        return Response(get_match_stats(fixture_id))
    except Exception as e:
        return Response({"error": str(e)}, status=503)
    
@api_view(['GET'])
def wc_live(request):
    from apps.matches.football_api import get_wc_live_matches
    try:
        return Response(get_wc_live_matches())
    except Exception as e:
        return Response([], status=200)
    
    
@api_view(['GET'])
def wc_live_scores(request):
    """Called every 30s by frontend JS."""
    from apps.matches.football_api import get_wc_live_matches, get_wc_all_matches
    from django.core.cache import cache

    # Force fresh data — bypass cache for live endpoint
    cache.delete('wc_all_matches')
    live = get_wc_live_matches()
    return Response(live)

@api_view(['GET'])  
def wc_all_data(request):
    """Returns live + today + results in one call."""
    from apps.matches.football_api import (
        get_wc_live_matches, get_wc_upcoming, get_wc_results
    )
    return Response({
        "live":     get_wc_live_matches(),
        "upcoming": get_wc_upcoming(),
        "results":  get_wc_results()[:6],
    })