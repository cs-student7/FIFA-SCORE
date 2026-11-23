import requests
from django.conf import settings
from django.core.cache import cache
from datetime import date, datetime

# ── api-sports.io ─────────────────────────────────────────────
AP_HEADERS = {"x-apisports-key": settings.API_FOOTBALL_KEY}
AP_BASE    = "https://v3.football.api-sports.io"

# ── World Cup 2026 API ────────────────────────────────────────
WC_BASE    = "http://worldcup26.ir:3050"

# Main leagues to display on LeaguePulse (add or remove any league ID here)
TRACKED_LEAGUES = {
    39:  {"name": "Premier League", "country": "England", "priority": 1},
    140: {"name": "La Liga", "country": "Spain", "priority": 2},
    2:   {"name": "UEFA Champions League", "country": "Europe", "priority": 3},
    135: {"name": "Serie A", "country": "Italy", "priority": 4},
    78:  {"name": "Bundesliga", "country": "Germany", "priority": 5},
    61:  {"name": "Ligue 1", "country": "France", "priority": 6},
}


def _ap_get(endpoint, params=None):
    if not settings.API_FOOTBALL_KEY:
        return []
    try:
        r = requests.get(
            f"{AP_BASE}/{endpoint}",
            headers=AP_HEADERS,
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("errors"):
            print("API-Football error:", data["errors"])
            return []
        return data.get("response", [])
    except Exception as e:
        print("API-Football request failed:", e)
        return []


def _wc_get(endpoint):
    """Call WC API with JWT token. Retries once, falls back to stale cache."""
    token = settings.WC_API_TOKEN
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    for attempt in range(2):
        try:
            r = requests.get(f"{WC_BASE}/{endpoint}", headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
            cache.set(f'stale_{endpoint}', data, 60 * 60 * 24)
            return data
        except Exception:
            if attempt == 0:
                continue
            stale = cache.get(f'stale_{endpoint}')
            return stale if stale else {}
    return {}


# ── api-sports functions (with caching + normalization) ───────
def get_live_matches():
    """
    1 API call returns ALL live matches across all tracked leagues.
    Cached for 3 minutes (180s) to stay safely within 100 req/day.
    Normalized to match static/js/goalpulse.js!
    """
    cached = cache.get("ap_live_matches")
    if cached is not None:
        return cached

    raw = _ap_get("fixtures", {"live": "all"})
    normalized = []
    for m in raw:
        league_id = m["league"]["id"]
        if league_id not in TRACKED_LEAGUES:
            continue
        elapsed = m["fixture"]["status"]["elapsed"]
        short_st = m["fixture"]["status"]["short"]
        normalized.append({
            "id": m["fixture"]["id"],
            "league_id": league_id,
            "league_name": m["league"]["name"],
            "league_logo": m["league"]["logo"],
            "home_team": {
                "name": m["teams"]["home"]["name"],
                "logo": m["teams"]["home"]["logo"],
            },
            "away_team": {
                "name": m["teams"]["away"]["name"],
                "logo": m["teams"]["away"]["logo"],
            },
            "home_score": m["goals"]["home"] or 0,
            "away_score": m["goals"]["away"] or 0,
            "status": "ht" if short_st == "HT" else "live",
            "display_minute": "HT" if short_st == "HT" else (f"{elapsed}'" if elapsed else "LIVE"),
        })

    normalized.sort(key=lambda x: TRACKED_LEAGUES.get(x["league_id"], {}).get("priority", 99))
    cache.set("ap_live_matches", normalized, 180)
    return normalized


def get_today_matches(league_id=None):
    """
    1 API call fetches today's fixtures across ALL tracked leagues (cached 1 hour).
    """
    today_str = str(date.today())
    cache_key = f"ap_today_matches_{today_str}_{league_id or 'all'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    params = {"date": today_str}
    if league_id:
        params["league"] = league_id

    raw = _ap_get("fixtures", params)
    filtered = [m for m in raw if m["league"]["id"] in TRACKED_LEAGUES]
    filtered.sort(key=lambda m: (
        TRACKED_LEAGUES[m["league"]["id"]]["priority"],
        m["fixture"]["timestamp"],
    ))

    cache.set(cache_key, filtered, 3600)
    return filtered


def get_league_standings(league_id=39, season=2026):
    """
    Standings for a league (cached 6 hours).
    """
    cache_key = f"ap_standings_{league_id}_{season}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    raw = _ap_get("standings", {"league": league_id, "season": season})
    standings = raw[0]["league"]["standings"][0] if raw else []
    cache.set(cache_key, standings, 21600)
    return standings


def get_match_events(fixture_id):
    cache_key = f"ap_events_{fixture_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = _ap_get("fixtures/events", {"fixture": fixture_id})
    cache.set(cache_key, data, 180)
    return data


def get_match_lineups(fixture_id):
    cache_key = f"ap_lineups_{fixture_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = _ap_get("fixtures/lineups", {"fixture": fixture_id})
    cache.set(cache_key, data, 3600)
    return data


def get_match_stats(fixture_id):
    cache_key = f"ap_stats_{fixture_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = _ap_get("fixtures/statistics", {"fixture": fixture_id})
    cache.set(cache_key, data, 180)
    return data


# ── World Cup 2026 (unchanged) ────────────────────────────────
def _parse_date(s):
    try:
        return datetime.strptime(s, "%m/%d/%Y %H:%M")
    except Exception:
        return None


def get_wc_all_matches():
    """All 104 WC matches — cached 60s."""
    cached = cache.get('wc_all_matches')
    if cached is not None:
        return cached
    data = _wc_get("get/games")
    matches = data.get("games", []) if isinstance(data, dict) else []
    cache.set('wc_all_matches', matches, 60)
    return matches


def _build_team_names():
    games = get_wc_all_matches()
    names = {}
    for g in games:
        for id_key, name_key in [
            ("home_team_id", "home_team_name_en"),
            ("away_team_id", "away_team_name_en"),
        ]:
            tid   = str(g.get(id_key, ""))
            tname = g.get(name_key, "")
            if tid and tid != "0" and tname:
                names[tid] = tname
    return names


def get_wc_live_matches():
    games = get_wc_all_matches()
    return [
        g for g in games
        if str(g.get("time_elapsed", "")).lower() not in ["finished", "notstarted", ""]
        and str(g.get("finished", "")).upper() != "TRUE"
    ]


def get_wc_today_matches():
    games = get_wc_all_matches()
    today = date.today()
    result = []
    for g in games:
        dt = _parse_date(g.get("local_date", ""))
        if dt and dt.date() == today:
            result.append(g)
    return result


def get_wc_upcoming():
    return [
        g for g in get_wc_today_matches()
        if str(g.get("time_elapsed", "")).lower() == "notstarted"
    ]


def get_wc_results():
    games = get_wc_all_matches()
    finished = [
        g for g in games
        if str(g.get("finished", "")).upper() == "TRUE"
    ]
    finished.sort(
        key=lambda g: _parse_date(g.get("local_date", "")) or datetime.min,
        reverse=True,
    )
    return finished[:20]


def get_wc_groups():
    cached = cache.get('wc_groups_enriched')
    if cached is not None:
        return cached

    groups_raw = _wc_get("get/groups")
    team_names = _build_team_names()

    if isinstance(groups_raw, dict):
        groups_list = groups_raw.get("groups") or groups_raw.get("data") or []
    elif isinstance(groups_raw, list):
        groups_list = groups_raw
    else:
        groups_list = []

    result = []
    for group in groups_list:
        enriched = []
        for team in group.get("teams", []):
            tid = str(team.get("team_id", ""))
            name = team_names.get(tid, "")
            if not name:
                continue
            enriched.append({
                "name": name,
                "mp":   int(team.get("mp", 0)),
                "w":    int(team.get("w",  0)),
                "d":    int(team.get("d",  0)),
                "l":    int(team.get("l",  0)),
                "pts":  int(team.get("pts", 0)),
                "gf":   int(team.get("gf", 0)),
                "ga":   int(team.get("ga", 0)),
                "gd":   int(team.get("gd", 0)),
            })
        enriched.sort(key=lambda t: (t["pts"], t["gd"], t["gf"]), reverse=True)
        if enriched:
            result.append({"name": group.get("name", ""), "teams": enriched})

    cache.set('wc_groups_enriched', result, 120)
    return result