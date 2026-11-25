import hashlib
import json
import requests
from django.conf import settings
from django.core.cache import cache
from datetime import date, datetime, timedelta, timezone as dt_timezone

# ── api-sports.io ─────────────────────────────────────────────
AP_HEADERS = {"x-apisports-key": settings.API_FOOTBALL_KEY}
AP_BASE    = settings.API_FOOTBALL_URL.rstrip("/")

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


def _ap_cache_keys(endpoint, params):
    serialized = json.dumps(params or {}, sort_keys=True, separators=(',', ':'))
    fingerprint = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    stale_key = f"ap_stale_{endpoint}_{fingerprint}"
    cooldown_key = f"ap_error_cooldown_{endpoint}_{fingerprint}"
    legacy_stale_key = f"ap_stale_{endpoint}_{params}"
    return stale_key, cooldown_key, legacy_stale_key


def _ap_get(endpoint, params=None):
    if not settings.API_FOOTBALL_KEY:
        return []

    stale_key, cooldown_key, legacy_stale_key = _ap_cache_keys(endpoint, params)

    def stale_response():
        stale = cache.get(stale_key)
        if stale is not None:
            return stale
        return cache.get(legacy_stale_key, [])

    if cache.get(cooldown_key):
        return stale_response()

    try:
        r = requests.get(
            f"{AP_BASE}/{endpoint}",
            headers=AP_HEADERS,
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        errors = data.get("errors")
        if errors:
            print("API-Football error:", errors)
            error_text = str(errors).lower()
            cooldown = 3600 if "limit" in error_text or "quota" in error_text else 60
            cache.set(cooldown_key, True, cooldown)
            return stale_response()
        cache.delete(cooldown_key)
        response = data.get("response", [])
        if response:
            cache.set(stale_key, response, 86400)  # 24-hour backup cache
        return response
    except Exception as e:
        print("API-Football request failed:", e)
        cache.set(cooldown_key, True, 60)
        return stale_response()


def _wc_get(endpoint):
    """Call the World Cup API briefly, then use stale data during outages."""
    token = settings.WC_API_TOKEN
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    stale_key = f"stale_{endpoint}"
    cooldown_key = f"wc_error_cooldown_{endpoint}"
    stale = cache.get(stale_key)
    if cache.get(cooldown_key):
        return stale if stale is not None else {}

    try:
        response = requests.get(
            f"{WC_BASE}/{endpoint}", headers=headers, timeout=3
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        print("World Cup API request failed:", error)
        cache.set(cooldown_key, True, 60)
        return stale if stale is not None else {}

    cache.set(stale_key, data, 60 * 60 * 24)
    cache.delete(cooldown_key)
    return data


# ── api-sports functions (with caching + normalization) ───────
def get_live_matches():
    """
    1 API call returns ALL live matches across all tracked leagues.
    Cached for one minute so the site stays responsive without every visitor
    creating another provider request.
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
    cache.set("ap_live_matches", normalized, 60)
    return normalized


def get_today_matches(league_id=None):
    """
    Fetches today's fixtures across ALL tracked leagues with a short live-safe cache.
    If today has 0 matches (e.g., quiet Monday), automatically fetches tomorrow's fixtures!
    """
    today_str = date.today().isoformat()
    filtered = get_fixtures_by_date(today_str, league_id=league_id)

    # Fallback to tomorrow's fixtures if today has 0 tracked matches
    if not filtered and not league_id:
        tomorrow_str = str(date.today() + timedelta(days=1))
        filtered = get_fixtures_by_date(tomorrow_str)

    if not filtered and (
        getattr(settings, "FIVE_DOLLAR_API_KEY", "")
        or getattr(settings, "FIVE_DOLLAR_API_KEY_2", "")
    ):
        filtered = _fd5_upcoming_or_today(today_str)
        if league_id:
            filtered = [
                match for match in filtered
                if match.get("league", {}).get("id") == league_id
            ]
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


def get_match_events(fixture_id, finished=False):
    cache_key = f"ap_events_{fixture_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = _ap_get("fixtures/events", {"fixture": fixture_id})
    cache.set(cache_key, data, 86400 if finished and data else 60)
    return data


def get_match_lineups(fixture_id):
    cache_key = f"ap_lineups_{fixture_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = _ap_get("fixtures/lineups", {"fixture": fixture_id})
    cache.set(cache_key, data, 3600 if data else 60)
    return data


def get_match_stats(fixture_id, finished=False):
    cache_key = f"ap_stats_{fixture_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = _ap_get("fixtures/statistics", {"fixture": fixture_id})
    cache.set(cache_key, data, 86400 if finished and data else 60)
    return data


def get_match_player_stats(fixture_id, finished=False):
    cache_key = f"ap_player_stats_{fixture_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = _ap_get("fixtures/players", {"fixture": fixture_id})
    cache.set(cache_key, data, 86400 if finished and data else 60)
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

def get_all_tracked_leagues():
    """Returns metadata + logos for all tracked leagues (0 API calls needed)."""
    return [
        {
            "id": lid,
            "name": info["name"],
            "country": info["country"],
            "logo": f"https://media.api-sports.io/football/leagues/{lid}.png",
        }
        for lid, info in TRACKED_LEAGUES.items()
    ]


def get_league_teams(league_id=39, season=2026):
    """Fetches all teams in a league (cached 24 hours -> 1 API call/day)."""
    cache_key = f"ap_teams_{league_id}_{season}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    raw = _ap_get("teams", {"league": league_id, "season": season})
    cache.set(cache_key, raw, 86400)
    return raw


def get_top_scorers(league_id=39, season=2026):
    """Fetches top scorers/players for a league (cached 12 hours)."""
    cache_key = f"ap_topscorers_{league_id}_{season}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    raw = _ap_get("players/topscorers", {"league": league_id, "season": season})
    cache.set(cache_key, raw, 43200)
    return raw
def get_fixtures_by_date(date_str, league_id=None):
    """
    Fetches fixtures for a specific YYYY-MM-DD date across all tracked leagues.
    """
    cache_key = f"ap_fixtures_date_{date_str}"
    cached = cache.get(cache_key)
    if cached is None:
        raw = _ap_get("fixtures", {"date": date_str})
        if not raw and getattr(settings, "FIVE_DOLLAR_API_KEY", ""):
            raw = _fd5_fixtures_for_date(date_str)
        cached = [m for m in raw if m["league"]["id"] in TRACKED_LEAGUES]
        cached.sort(key=lambda m: (
            TRACKED_LEAGUES[m["league"]["id"]]["priority"],
            m["fixture"]["timestamp"],
        ))
        cache.set(cache_key, cached, 180)

    if league_id:
        return [m for m in cached if m["league"]["id"] == league_id]
    return cached

def get_fixture_full_details(fixture_id):
    """
    Combines fixture, event, lineup, statistics and player-rating data for the match center.
    """
    cache_key = f"ap_fixture_full_{fixture_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    raw = _ap_get("fixtures", {"id": fixture_id})
    if not raw:
        return {}

    item = raw[0]
    status_short = item.get("fixture", {}).get("status", {}).get("short", "NS")
    finished_statuses = {"FT", "AET", "PEN", "CANC", "ABD", "AWD", "WO"}
    finished = status_short in finished_statuses
    item["events"] = get_match_events(fixture_id, finished=finished)
    item["lineups"] = get_match_lineups(fixture_id)
    item["statistics"] = get_match_stats(fixture_id, finished=finished)
    item["players"] = get_match_player_stats(fixture_id, finished=finished)
    details_complete = all(
        item[key] for key in ("events", "lineups", "statistics", "players")
    )
    ttl = 86400 if finished and details_complete else 3600 if finished else 60
    cache.set(cache_key, item, ttl)
    return item

FIVE_DOLLAR_BASE = "https://api.5dollarfootballapi.com/v1"


def _fd5_get(endpoint, params=None):
    """Calls 5DollarFootballAPI with automatic fallback between two keys."""
    keys = [
        key
        for key in (
            getattr(settings, "FIVE_DOLLAR_API_KEY", ""),
            getattr(settings, "FIVE_DOLLAR_API_KEY_2", ""),
        )
        if key
    ]
    if not keys:
        return []

    serialized_params = json.dumps(
        params or {}, sort_keys=True, separators=(",", ":")
    )
    fingerprint = hashlib.sha256(
        f"{endpoint}:{serialized_params}".encode("utf-8")
    ).hexdigest()
    stale_key = f"fd5_stale_{fingerprint}"
    last_error = None
    for key in keys:
        try:
            response = requests.get(
                f"{FIVE_DOLLAR_BASE}/{endpoint.lstrip('/')}",
                headers={"Authorization": f"Bearer {key}"},
                params=params,
                timeout=10,
            )
        except requests.RequestException as error:
            last_error = error
            continue

        if response.status_code in (401, 403, 429):
            last_error = requests.HTTPError(
                f"5DollarFootballAPI returned HTTP {response.status_code}"
            )
            continue

        try:
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            last_error = error
            continue

        if not isinstance(payload, dict):
            last_error = ValueError("5DollarFootballAPI returned an invalid response")
            continue

        data = payload.get("data", [])
        if data:
            cache.set(stale_key, data, 86400)
        return data

    if last_error:
        print(f"5DollarFootballAPI request failed for {endpoint}: {last_error}")
    else:
        print(f"5DollarFootballAPI rejected all configured keys for {endpoint}")
    return cache.get(stale_key, [])


def _normalize_fd5_fixture(item):
    """Converts a 5DollarFootballAPI fixture object into the template/frontend match format."""
    home = item.get("home_team") or item.get("home") or {}
    away = item.get("away_team") or item.get("away") or {}
    league = item.get("league") or {}
    score = item.get("score") or {}
    status_raw = str(item.get("status", "scheduled")).lower()

    status_map = {
        "live": "LIVE",
        "in_play": "1H",
        "ht": "HT",
        "halftime": "HT",
        "finished": "FT",
        "ft": "FT",
        "scheduled": "NS",
    }

    return {
        "fixture": {
            "id": item.get("id"),
            "date": item.get("kickoff_at") or item.get("date") or "",
            "timestamp": item.get("timestamp") or 0,
            "status": {
                "short": status_map.get(status_raw, "NS"),
                "elapsed": item.get("minute") or item.get("elapsed"),
            },
        },
        "league": {
            "id": league.get("id", 0),
            "name": league.get("name", "Top League"),
            "logo": league.get("logo") or f"https://media.api-sports.io/football/leagues/{league.get('id', 39)}.png",
        },
        "teams": {
            "home": {
                "id": home.get("id"),
                "name": home.get("name", "Home"),
                "logo": home.get("logo") or "",
            },
            "away": {
                "id": away.get("id"),
                "name": away.get("name", "Away"),
                "logo": away.get("logo") or "",
            },
        },
        "goals": {
            "home": score.get("home", item.get("home_score")),
            "away": score.get("away", item.get("away_score")),
        },
        "events": item.get("events", []),
        "statistics": item.get("stats") or item.get("statistics") or [],
    }


def _fd5_fixtures_for_date(date_str):
    day_start = datetime.strptime(date_str, "%Y-%m-%d").replace(
        tzinfo=dt_timezone.utc
    )
    start_ts = int(day_start.timestamp())
    end_ts = start_ts + 86400
    raw = _fd5_get(
        "fixtures",
        {"start_time": start_ts, "end_time": end_ts, "include": "events,stats"},
    )
    return [_normalize_fd5_fixture(match) for match in raw]


def _fd5_upcoming_or_today(date_str):
    """Return today's provider fixtures, or the next scheduled fixtures."""
    cache_key = f"fd5_upcoming_or_today_{date_str}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    today_fixtures = _fd5_fixtures_for_date(date_str)
    if today_fixtures:
        cache.set(cache_key, today_fixtures, 900)
        return today_fixtures

    leagues = _fd5_get("leagues")
    upcoming = []
    for league in leagues[:5]:
        if not isinstance(league, dict):
            continue
        league_id = league.get("id")
        if not league_id:
            continue
        raw_fixtures = _fd5_get(
            f"leagues/{league_id}/fixtures",
            {"status": "scheduled", "per_page": 5},
        )
        upcoming.extend(
            _normalize_fd5_fixture(match) for match in raw_fixtures
        )

    upcoming.sort(
        key=lambda match: match.get("fixture", {}).get("timestamp") or 0
    )
    cache.set(cache_key, upcoming, 900 if upcoming else 120)
    return upcoming