from django.views.generic import DetailView, ListView
from django.core.cache import cache
from .models import Competition, Season, Standing


class LeagueListView(ListView):
    model = Competition
    template_name = 'leagues/list.html'
    context_object_name = 'competitions'
    queryset = Competition.objects.filter(is_active=True).select_related('country').order_by('tier', 'name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['featured'] = self.queryset.filter(is_featured=True)
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
            
            # Cache standings for 5 minutes
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