from django.views.generic import DetailView, TemplateView
from django.core.cache import cache
from .models import Competition
from apps.matches.football_api import (
    TRACKED_LEAGUES,
    get_all_tracked_leagues,
    get_league_standings,
)


class LeagueListView(TemplateView):
    template_name = 'leagues/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            active_league = int(self.request.GET.get('league', 39))
        except ValueError:
            active_league = 39

        if active_league not in TRACKED_LEAGUES:
            active_league = 39

        ctx['api_leagues'] = get_all_tracked_leagues()
        ctx['active_league'] = active_league
        ctx['active_league_info'] = TRACKED_LEAGUES[active_league]
        ctx['standings'] = get_league_standings(league_id=active_league, season=2026)
        ctx['competitions'] = Competition.objects.filter(is_active=True).select_related('country').order_by('tier', 'name')
        return ctx


class LeagueDetailView(DetailView):
    model = Competition
    template_name = 'leagues/detail.html'
    context_object_name = 'competition'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        season = self.object.seasons.filter(is_current=True).first()
        if season:
            ctx['season'] = season
            cache_key = f'standings_{season.id}'
            standings = cache.get(cache_key)
            if not standings:
                standings = list(season.standings.select_related('team').order_by('position'))
                cache.set(cache_key, standings, 300)
            ctx['standings'] = standings
            ctx['top_scorers'] = season.top_scorers.select_related('player', 'team').order_by('rank')[:10]
            from apps.matches.models import Match
            ctx['recent_matches'] = Match.objects.filter(
                season=season, status='ft'
            ).select_related('home_team', 'away_team').order_by('-kickoff')[:10]
            ctx['upcoming_matches'] = Match.objects.filter(
                season=season, status='scheduled'
            ).select_related('home_team', 'away_team').order_by('kickoff')[:10]
        return ctx