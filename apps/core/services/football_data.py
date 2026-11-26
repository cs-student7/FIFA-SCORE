from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.cache import cache


FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"
FEATURED_COMPETITIONS = ["PL", "BL1", "PD", "SA", "CL"]


class FootballDataClient:
    def __init__(self):
        self.headers = {
            "X-Auth-Token": settings.API_TOKEN,
        }

    def _get(self, path, params=None):
        response = requests.get(
            f"{FOOTBALL_DATA_BASE_URL}/{path.lstrip('/')}",
            headers=self.headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_competition(self, code):
        return self._get(f"competitions/{code}")

    def get_matches(self, code, status=None):
        cache_key = f"{code.lower()}_matches_v4"
        if status:
            cache_key = f"{cache_key}_{status.lower()}"
        cached_matches = cache.get(cache_key)
        if cached_matches is not None:
            return cached_matches

        params = {"status": status} if status else None
        data = self._get(f"competitions/{code}/matches", params=params)
        matches = data.get("matches", [])
        cache.set(cache_key, matches, 120)
        return matches

    def get_matches_by_date(self, date_from, date_to, competitions, status=None):
        competition_codes = ",".join(competitions)
        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "competitions": competition_codes,
        }
        if status:
            params["status"] = status

        cache_key = (
            f"football_data_matches_v4_{date_from}_{date_to}_"
            f"{competition_codes}_{status or 'all'}"
        )
        matches = cache.get(cache_key)
        if matches is not None:
            return matches

        data = self._get("matches", params=params)
        matches = data.get("matches", [])
        cache.set(cache_key, matches, 60 if status == "LIVE" else 120)
        return matches

    def get_live_matches(self, competitions):
        competition_codes = ",".join(competitions)
        cache_key = f"football_data_live_matches_v4_{competition_codes}"
        matches = cache.get(cache_key)
        if matches is not None:
            return matches

        data = self._get(
            "matches",
            params={"competitions": competition_codes, "status": "LIVE"},
        )
        matches = data.get("matches", [])
        cache.set(cache_key, matches, 60)
        return matches

    def get_teams(self, code):
        cache_key = f"football_data_teams_v4_{code.lower()}"
        teams = cache.get(cache_key)
        if teams is None:
            data = self._get(f"competitions/{code}/teams")
            teams = data.get("teams", [])
            cache.set(cache_key, teams, 86400)
        return teams

    def get_standings(self, code):
        cache_key = f"football_data_standings_v4_{code.lower()}"
        standings = cache.get(cache_key)
        if standings is None:
            standings = self._get(f"competitions/{code}/standings")
            cache.set(cache_key, standings, 21600)
        return standings

    def get_scorers(self, code):
        cache_key = f"football_data_scorers_v4_{code.lower()}"
        scorers = cache.get(cache_key)
        if scorers is None:
            data = self._get(f"competitions/{code}/scorers")
            scorers = data.get("scorers", [])
            cache.set(cache_key, scorers, 21600)
        return scorers

    def get_match(self, match_id):
        cache_key = f"football_data_match_v4_{match_id}"
        match = cache.get(cache_key)
        if match is None:
            match = self._get(f"matches/{match_id}")
            cache.set(cache_key, match, 60)
        return match


def download_image(url):
    if not url:
        return None

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        name = urlparse(url).path.rsplit("/", 1)[-1] or "image"
        return ContentFile(response.content, name=name)
    except requests.RequestException:
        return None