import hashlib
import json
import logging
from datetime import date, timedelta
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.cache import cache


FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"
FEATURED_COMPETITIONS = ["PL", "BL1", "PD", "SA", "CL"]
logger = logging.getLogger(__name__)


def _get_v4(endpoint, params=None, ttl=120):
    params_json = json.dumps(params or {}, sort_keys=True, separators=(",", ":"))
    cache_hash = hashlib.sha256(
        f"{endpoint}:{params_json}".encode("utf-8")
    ).hexdigest()
    cache_key = f"fd_v4_{cache_hash}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    token = settings.API_TOKEN.strip()
    if not token:
        raise ValueError("API_TOKEN is required for football-data.org v4.")

    response = requests.get(
        f"{FOOTBALL_DATA_BASE_URL}{endpoint}",
        headers={"X-Auth-Token": token},
        params=params,
        timeout=10,
    )
    try:
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        logger.exception("football-data.org v4 request failed for %s", endpoint)
        raise

    cache.set(cache_key, data, ttl)
    return data


def get_matches_by_date(date_from, date_to, competitions=None, status=None):
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
    }
    if competitions:
        params["competitions"] = ",".join(competitions)
    if status:
        params["status"] = status
    ttl = 60 if status == "LIVE" else 120
    return _get_v4("/matches", params=params, ttl=ttl).get("matches", [])


def get_weekly_matches(competitions=None, status=None):
    today = date.today()
    return get_matches_by_date(
        (today - timedelta(days=2)).isoformat(),
        (today + timedelta(days=5)).isoformat(),
        competitions=competitions,
        status=status,
    )


def get_standings(code="PL"):
    data = _get_v4(f"/competitions/{code}/standings", ttl=600)
    standings = data.get("standings", [])
    if not standings:
        return []
    total = next(
        (table for table in standings if table.get("type") == "TOTAL"),
        standings[0],
    )
    return total.get("table", [])


def get_top_scorers(code="PL", limit=10):
    return _get_v4(
        f"/competitions/{code}/scorers",
        params={"limit": limit},
        ttl=600,
    ).get("scorers", [])


class FootballDataClient:
    def _get(self, path, params=None, ttl=120):
        return _get_v4(f"/{path.lstrip('/')}", params=params, ttl=ttl)

    def get_competition(self, code):
        return self._get(f"competitions/{code}")

    def get_matches(self, code, status=None):
        params = {"status": status} if status else None
        data = self._get(f"competitions/{code}/matches", params=params)
        return data.get("matches", [])

    def get_matches_by_date(self, date_from, date_to, competitions, status=None):
        return get_matches_by_date(
            date_from, date_to, competitions=competitions, status=status
        )

    def get_live_matches(self, competitions):
        competition_codes = ",".join(competitions)
        data = self._get(
            "matches",
            params={"competitions": competition_codes, "status": "LIVE"},
            ttl=60,
        )
        return data.get("matches", [])

    def get_teams(self, code):
        data = _get_v4(f"/competitions/{code}/teams", ttl=86400)
        return data.get("teams", [])

    def get_standings(self, code):
        return _get_v4(f"/competitions/{code}/standings", ttl=600)

    def get_scorers(self, code):
        data = _get_v4(f"/competitions/{code}/scorers", ttl=600)
        return data.get("scorers", [])

    def get_match(self, match_id):
        return _get_v4(f"/matches/{match_id}", ttl=60)


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