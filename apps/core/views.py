from django.views.generic import TemplateView
from django.utils import timezone
from django.core.cache import cache
from apps.leagues.models import Competition
from apps.matches.football_api import (
    get_wc_live_matches, get_wc_upcoming,
    get_wc_results, get_wc_groups,
)

class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # ── World Cup 2026 (free API, no key needed) ──────────
        try:
            ctx['wc_live']     = get_wc_live_matches()
            ctx['wc_upcoming'] = get_wc_upcoming()
            ctx['wc_results']  = get_wc_results()
            ctx['wc_groups']   = get_wc_groups()
        except Exception as e:
            ctx['wc_live'] = []
            ctx['wc_upcoming'] = []
            ctx['wc_results'] = []
            ctx['wc_groups'] = []

        # ── Featured competitions + standings (from DB) ────────
        featured = list(
            Competition.objects.filter(
                is_featured=True, is_active=True
            )[:6]
        )
        ctx['featured_competitions'] = featured
        ctx['competition_standings'] = []
        for comp in featured:
            season = comp.seasons.filter(is_current=True).first()
            if season:
                standings = season.standings.select_related(
                    'team'
                ).order_by('position')[:20]
                ctx['competition_standings'].append({
                    'competition': comp,
                    'season': season,
                    'standings': standings,
                })

        # ── Top scorers (from DB) ──────────────────────────────
        ctx['top_scorers'] = []
        if featured:
            season = featured[0].seasons.filter(
                is_current=True
            ).first()
            if season:
                ctx['top_scorers'] = (
                    season.top_scorers
                    .select_related('player', 'team')
                    .order_by('rank')[:10]
                )

        return ctx