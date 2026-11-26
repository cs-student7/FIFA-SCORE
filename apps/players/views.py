import logging
import requests
from django.views.generic import DetailView, TemplateView
from apps.core.services.football_data import get_top_scorers as get_fd_top_scorers
from .models import Player
from apps.matches.football_api import (
    TRACKED_LEAGUES,
    get_all_tracked_leagues,
)

logger = logging.getLogger(__name__)


class PlayerListView(TemplateView):
    template_name = 'players/list.html'

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
            api_players = get_fd_top_scorers(
                code=TRACKED_LEAGUES[active_league]['code'], limit=20
            )
            ctx['api_error'] = ''
        except (requests.RequestException, ValueError):
            logger.exception(
                "Could not load scorers for league %s", active_league
            )
            api_players = []
            ctx['api_error'] = (
                "Player statistics are unavailable. Check your API_TOKEN and "
                "football-data.org account access, then try again."
            )

        if q:
            api_players = [
                item for item in api_players
                if q in item.get('player', {}).get('name', '').lower()
                or q in item.get('team', {}).get('name', '').lower()
            ]

        ctx['api_leagues'] = get_all_tracked_leagues()
        ctx['active_league'] = active_league
        ctx['api_players'] = api_players
        ctx['search_query'] = self.request.GET.get('q', '')
        return ctx


class PlayerDetailView(DetailView):
    model = Player
    template_name = 'players/detail.html'
    context_object_name = 'player'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.matches.models import MatchEvent
        ctx['goal_events'] = MatchEvent.objects.filter(
            player=self.object, event_type__in=['goal', 'penalty']
        ).select_related('match__home_team', 'match__away_team').order_by('-match__kickoff')[:10]
        return ctx