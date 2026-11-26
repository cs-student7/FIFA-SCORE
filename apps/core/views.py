import logging

import requests
from django.views.generic import TemplateView
from django.core.cache import cache
from apps.leagues.models import Competition
from apps.core.services.football_data import get_weekly_matches
from apps.matches.football_api import (
    get_wc_live_matches, get_wc_upcoming,
    get_wc_results, get_wc_groups,
    TRACKED_LEAGUES,
)

logger = logging.getLogger(__name__)


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

        # ── Weekly matches from football-data.org v4 ─────────
        try:
            codes = [info['code'] for info in TRACKED_LEAGUES.values()]
            matches = get_weekly_matches(competitions=codes)
            ctx['league_live'] = [
                match for match in matches
                if match.get('status') in {
                    'LIVE', 'IN_PLAY', 'PAUSED', 'EXTRA_TIME',
                    'PENALTY_SHOOTOUT',
                }
            ]
            ctx['league_today'] = matches
            ctx['tracked_leagues'] = TRACKED_LEAGUES
            ctx['league_fixtures_label'] = "Matches This Week"
        except (requests.RequestException, ValueError):
            logger.exception("Could not load football provider data for the home page")
            ctx['league_live']     = []
            ctx['league_today']    = []
            ctx['tracked_leagues'] = TRACKED_LEAGUES
            ctx['football_data_error'] = (
                "Match data is unavailable. Check your API_TOKEN and "
                "football-data.org account access, then try again."
            )

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