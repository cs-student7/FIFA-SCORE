from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.teams.models import Team
from apps.players.models import Player
from apps.leagues.models import Competition
from apps.teams.serializers import TeamSerializer
from apps.players.serializers import PlayerSerializer
from apps.leagues.serializers import CompetitionSerializer


class GlobalSearchAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.GET.get('q', '').strip()
        if len(q) < 2:
            return Response({'teams': [], 'players': [], 'competitions': []})

        teams = Team.objects.filter(name__icontains=q).select_related('country')[:5]
        players = Player.objects.filter(
            display_name__icontains=q
        ).select_related('current_team', 'nationality')[:5]
        competitions = Competition.objects.filter(
            name__icontains=q, is_active=True
        ).select_related('country')[:5]

        return Response({
            'teams': TeamSerializer(teams, many=True).data,
            'players': PlayerSerializer(players, many=True).data,
            'competitions': CompetitionSerializer(competitions, many=True).data,
        })
