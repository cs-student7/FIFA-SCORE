import logging
import requests
from datetime import date, timedelta
from django.views.generic import DetailView, TemplateView
from django.utils import timezone
from .models import Match
from apps.core.services.football_data import (
    get_matches_by_date as get_fd_matches_by_date,
)
from .football_api import (
    TRACKED_LEAGUES,
    get_all_tracked_leagues,
)

logger = logging.getLogger(__name__)


class MatchListView(TemplateView):
    template_name = 'matches/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        selected_date = self.request.GET.get('date') or today.isoformat()

        try:
            league_id = int(self.request.GET.get('league', 0)) or None
        except ValueError:
            league_id = None
        if league_id not in TRACKED_LEAGUES:
            league_id = None

        try:
            requested_day = date.fromisoformat(selected_date)
            competition_codes = (
                [TRACKED_LEAGUES[league_id]['code']]
                if league_id in TRACKED_LEAGUES
                else [
                    info['code'] for info in TRACKED_LEAGUES.values()
                ]
            )
            api_matches = get_fd_matches_by_date(
                selected_date, selected_date, competitions=competition_codes
            )
            api_matches.sort(key=lambda match: match.get('utcDate', ''))
            fixtures_fallback = False
            if not api_matches and requested_day >= today:
                api_matches = get_fd_matches_by_date(
                    selected_date,
                    (requested_day + timedelta(days=14)).isoformat(),
                    competitions=competition_codes,
                )
                api_matches.sort(key=lambda match: match.get('utcDate', ''))
                fixtures_fallback = bool(api_matches)
            api_error = ''
        except (requests.RequestException, ValueError):
            logger.exception("Could not load fixtures for %s", selected_date)
            api_matches = []
            fixtures_fallback = False
            api_error = (
                "Fixtures are unavailable. Check your API_TOKEN and "
                "football-data.org account access, then try again."
            )

        live_statuses = {
            'LIVE', 'IN_PLAY', 'PAUSED', 'EXTRA_TIME', 'PENALTY_SHOOTOUT',
        }

        ctx['api_matches'] = api_matches
        ctx['api_error'] = api_error
        ctx['fixtures_fallback'] = fixtures_fallback
        ctx['selected_date'] = selected_date
        ctx['yesterday_date'] = (today - timedelta(days=1)).isoformat()
        ctx['today_date'] = today.isoformat()
        ctx['tomorrow_date'] = (today + timedelta(days=1)).isoformat()
        ctx['api_leagues'] = get_all_tracked_leagues()
        ctx['active_league'] = league_id or 0
        ctx['live_count'] = sum(
            1 for m in api_matches if m.get('status') in live_statuses
        )
        return ctx


class MatchDetailView(DetailView):
    model = Match
    template_name = 'matches/detail.html'
    context_object_name = 'match'

    def get_queryset(self):
        return Match.objects.select_related(
            'home_team__country', 'away_team__country', 'season__competition__country'
        ).prefetch_related('events__player', 'events__team', 'statistics', 'momentum_data')


class FixtureCenterView(TemplateView):
    template_name = 'matches/fixture_center.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fixture_id'] = self.kwargs['fixture_id']
        return context