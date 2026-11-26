# apps/core/football_api.py
import requests
from datetime import datetime, timezone
from django.conf import settings
from django.core.cache import cache

TRACKED_LEAGUES = {
    39:  {"name": "Premier League", "short_name": "EPL", "slug": "premier-league", "country": "England", "priority": 1},
    140: {"name": "La Liga", "short_name": "La Liga", "slug": "la-liga", "country": "Spain", "priority": 2},
    2:   {"name": "UEFA Champions League", "short_name": "UCL", "slug": "champions-league", "country": "Europe", "priority": 3},
    135: {"name": "Serie A", "short_name": "Serie A", "slug": "serie-a", "country": "Italy", "priority": 4},
    78:  {"name": "Bundesliga", "short_name": "Bundesliga", "slug": "bundesliga", "country": "Germany", "priority": 5},
}


def _fetch_apifootball(endpoint, params=None):
    api_key = getattr(settings, "API_FOOTBALL_KEY", "")
    if not api_key:
        return []
    try:
        res = requests.get(
            f"{settings.API_FOOTBALL_URL}/{endpoint}",
            headers={"x-apisports-key": api_key},
            params=params,
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()
        return [] if data.get("errors") else data.get("response", [])
    except requests.RequestException as error:
        print("API-Football error:", error)
    return []


def get_live_matches_normalized():
    """
    1 API call for ALL live matches across your tracked leagues (cached 3 mins).
    Returns the exact JSON shape expected by static/js/goalpulse.js!
    """
    cached = cache.get("apifb_live_matches")
    if cached is not None:
        return cached

    raw = _fetch_apifootball("fixtures", {"live": "all"})
    results = []
    for m in raw:
        league_id = m["league"]["id"]
        if league_id not in TRACKED_LEAGUES:
            continue
        elapsed = m["fixture"]["status"]["elapsed"]
        short_status = m["fixture"]["status"]["short"]
        results.append({
            "id": m["fixture"]["id"],
            "league_id": league_id,
            "league_name": m["league"]["name"],
            "league_logo": m["league"]["logo"],
            "home_team": {"name": m["teams"]["home"]["name"], "logo": m["teams"]["home"]["logo"]},
            "away_team": {"name": m["teams"]["away"]["name"], "logo": m["teams"]["away"]["logo"]},
            "home_score": m["goals"]["home"] or 0,
            "away_score": m["goals"]["away"] or 0,
            "status": "ht" if short_status == "HT" else "live",
            "display_minute": "HT" if short_status == "HT" else (f"{elapsed}'" if elapsed else "LIVE"),
        })

    cache.set("apifb_live_matches", results, timeout=180)
    return results


def get_today_fixtures_by_league(date_str=None):
    """
    1 API call for all today's fixtures across all tracked leagues (cached 1 hour).
    """
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cache_key = f"apifb_fixtures_{date_str}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    raw = _fetch_apifootball("fixtures", {"date": date_str})
    filtered = [m for m in raw if m["league"]["id"] in TRACKED_LEAGUES]
    filtered.sort(key=lambda m: (TRACKED_LEAGUES[m["league"]["id"]]["priority"], m["fixture"]["timestamp"]))

    cache.set(cache_key, filtered, timeout=3600)
    return filtered


def get_league_standings(league_id, season=2026):
    """
    Standings for one league (cached 6 hours).
    """
    cache_key = f"apifb_standings_{league_id}_{season}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    raw = _fetch_apifootball("standings", {"league": league_id, "season": season})
    standings = raw[0]["league"]["standings"][0] if raw else []
    cache.set(cache_key, standings, timeout=21600)
    return standings
