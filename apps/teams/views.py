import logging
import requests
from django.views.generic import DetailView, TemplateView
from django.db.models import Q
from .models import Team
from apps.matches.football_api import (
    TRACKED_LEAGUES,
    get_all_tracked_leagues,
    get_league_teams,
)

logger = logging.getLogger(__name__)


class TeamListView(TemplateView):
    template_name = 'teams/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            active_league = int(self.request.GET.get('league', 39))
        except ValueError:
            active_league = 39

        if active_league not in TRACKED_LEAGUES:
            active_league = 39

        q = self.request.GET.get('q', '').strip().lower()
        try:
            api_teams = get_league_teams(
                league_id=active_league, season=2026
            )
            ctx['api_error'] = ''
        except (requests.RequestException, ValueError):
            logger.exception("Could not load teams for league %s", active_league)
            api_teams = []
            ctx['api_error'] = (
                "Teams are unavailable. Check your API_TOKEN and "
                "football-data.org account access, then try again."
            )

        if q:
            api_teams = [
                item for item in api_teams
                if q in item.get('team', {}).get('name', '').lower()
                or q in item.get('venue', {}).get('city', '').lower()
            ]

        ctx['api_leagues'] = get_all_tracked_leagues()
        ctx['active_league'] = active_league
        ctx['api_teams'] = api_teams
        ctx['search_query'] = self.request.GET.get('q', '')
        return ctx


class TeamDetailView(DetailView):
    model = Team
    template_name = 'teams/detail.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.matches.models import Match
        ctx['recent_matches'] = Match.objects.filter(
            Q(home_team=self.object) | Q(away_team=self.object),
            status='ft'
        ).select_related('home_team', 'away_team', 'season__competition').order_by('-kickoff')[:6]
        ctx['upcoming_matches'] = Match.objects.filter(
            Q(home_team=self.object) | Q(away_team=self.object),
            status='scheduled'
        ).select_related('home_team', 'away_team', 'season__competition').order_by('kickoff')[:5]
        ctx['players'] = self.object.players.filter(is_active=True).order_by('position', 'shirt_number')
        return ctx