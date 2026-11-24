from datetime import date, timedelta
from django.views.generic import DetailView, TemplateView
from django.utils import timezone
from .models import Match
from .football_api import (
    TRACKED_LEAGUES,
    get_all_tracked_leagues,
    get_fixtures_by_date,
)


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

        api_matches = get_fixtures_by_date(selected_date, league_id=league_id)
        live_statuses = {'1H', '2H', 'HT', 'ET', 'P', 'BT', 'LIVE'}

        ctx['api_matches'] = api_matches
        ctx['selected_date'] = selected_date
        ctx['yesterday_date'] = (today - timedelta(days=1)).isoformat()
        ctx['today_date'] = today.isoformat()
        ctx['tomorrow_date'] = (today + timedelta(days=1)).isoformat()
        ctx['api_leagues'] = get_all_tracked_leagues()
        ctx['active_league'] = league_id or 0
        ctx['live_count'] = sum(
            1 for m in api_matches
            if m.get('fixture', {}).get('status', {}).get('short') in live_statuses
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