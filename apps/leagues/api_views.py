from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Season, Competition
from .serializers import CompetitionSerializer, SeasonSerializer
from apps.matches.serializers import StandingSerializer
from apps.matches.models import TopScorer
from apps.players.serializers import PlayerSerializer


class CompetitionListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CompetitionSerializer
    queryset = Competition.objects.filter(is_active=True).select_related('country').order_by('tier', 'name')


class CompetitionDetailAPIView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = CompetitionSerializer
    queryset = Competition.objects.select_related('country')


class StandingsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, season_id):
        try:
            season = Season.objects.get(pk=season_id)
        except Season.DoesNotExist:
            return Response({'error': 'Season not found'}, status=404)
        standings = season.standings.select_related('team').order_by('position')
        return Response(StandingSerializer(standings, many=True).data)


class TopScorersAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, season_id):
        try:
            season = Season.objects.get(pk=season_id)
        except Season.DoesNotExist:
            return Response({'error': 'Season not found'}, status=404)
        scorers = season.top_scorers.select_related('player', 'team').order_by('rank')[:20]
        from apps.matches.serializers import TopScorerSerializer
        return Response(TopScorerSerializer(scorers, many=True).data)
