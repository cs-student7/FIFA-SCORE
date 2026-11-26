import hashlib
import json
import requests
from django.conf import settings
from django.core.cache import cache
from datetime import date, datetime, timedelta
from apps.core.services.football_data import FootballDataClient

# ── api-sports.io ─────────────────────────────────────────────
AP_BASE    = settings.API_FOOTBALL_URL.rstrip("/")

# ── World Cup 2026 API ────────────────────────────────────────
WC_BASE    = "http://worldcup26.ir:3050"

# Main leagues to display on LeaguePulse (add or remove any league ID here)
TRACKED_LEAGUES = {
    39:  {"name": "Premier League", "country": "England", "priority": 1, "code": "PL"},
    140: {"name": "La Liga", "country": "Spain", "priority": 2, "code": "PD"},
    2:   {"name": "UEFA Champions League", "country": "Europe", "priority": 3, "code": "CL"},
    135: {"name": "Serie A", "country": "Italy", "priority": 4, "code": "SA"},
    78:  {"name": "Bundesliga", "country": "Germany", "priority": 5, "code": "BL1"},
    61:  {"name": "Ligue 1", "country": "France", "priority": 6, "code": "FL1"},
}

FOOTBALL_DATA_LEAGUE_IDS = {
    info["code"]: league_id for league_id, info in TRACKED_LEAGUES.items()
}


def _football_data_fixture(match):
    competition = match.get("competition") or {}
    code = competition.get("code")
    league_id = FOOTBALL_DATA_LEAGUE_IDS.get(code)
    if league_id is None:
        return None

    fixture_status = match.get("status", "SCHEDULED")
    status_map = {
        "SCHEDULED": "NS",
        "TIMED": "NS",
        "IN_PLAY": "1H",
        "PAUSED": "HT",
        "EXTRA_TIME": "ET",
        "PENALTY_SHOOTOUT": "P",
        "FINISHED": "FT",
        "POSTPONED": "PST",
        "SUSPENDED": "SUSP",
        "CANCELLED": "CANC",
        "AWARDED": "AWD",
    }

    def normalized_team(team):
        return {
            "id": team.get("id"),
            "name": team.get("name", "TBD"),
            "logo": team.get("crest") or "",
        }

    score = match.get("score") or {}
    full_time = score.get("fullTime") or {}
    utc_date = match.get("utcDate", "")
    try:
        timestamp = int(
            datetime.fromisoformat(utc_date.replace("Z", "+00:00")).timestamp()
        )
    except (ValueError, TypeError):
        timestamp = 0

    return {
        "fixture": {
            "id": match.get("id"),
            "date": utc_date,
            "timestamp": timestamp,
            "status": {
                "short": status_map.get(fixture_status, fixture_status),
                "long": fixture_status.replace("_", " ").title(),
                "elapsed": None,
            },
        },
        "league": {
            "id": league_id,
            "name": competition.get("name") or TRACKED_LEAGUES[league_id]["name"],
            "logo": competition.get("emblem") or "",
            "round": match.get("matchday") or match.get("stage", ""),
        },
        "teams": {
            "home": normalized_team(match.get("homeTeam") or {}),
            "away": normalized_team(match.get("awayTeam") or {}),
        },
        "goals": {
            "home": full_time.get("home"),
            "away": full_time.get("away"),
        },
    }


def _football_data_fixtures(date_from, date_to, league_id=None, status=None):
    if league_id is not None and league_id not in TRACKED_LEAGUES:
        return []
    codes = (
        [TRACKED_LEAGUES[league_id]["code"]]
        if league_id is not None
        else [info["code"] for info in TRACKED_LEAGUES.values()]
    )
    matches = FootballDataClient().get_matches_by_date(
        date_from, date_to, codes, status=status
    )
    fixtures = []
    for match in matches:
        fixture = _football_data_fixture(match)
        if fixture is not None:
            fixtures.append(fixture)
    fixtures.sort(key=lambda item: (
        TRACKED_LEAGUES[item["league"]["id"]]["priority"],
        item["fixture"]["timestamp"],
    ))
    return fixtures


def _ap_cache_keys(endpoint, params):
    serialized = json.dumps(params or {}, sort_keys=True, separators=(',', ':'))
    fingerprint = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    stale_key = f"ap_stale_{endpoint}_{fingerprint}"
    cooldown_key = f"ap_error_cooldown_{endpoint}_{fingerprint}"
    legacy_stale_key = f"ap_stale_{endpoint}_{params}"
    return stale_key, cooldown_key, legacy_stale_key


def _ap_get(endpoint, params=None):
    keys = list(dict.fromkeys(
        key for key in (
            getattr(settings, "API_FOOTBALL_KEY", ""),
        ) if key
    ))
    if not keys:
        return []

    stale_key, cooldown_key, legacy_stale_key = _ap_cache_keys(endpoint, params)

    def stale_response():
        stale = cache.get(stale_key)
        if stale is not None:
            return stale
        return cache.get(legacy_stale_key, [])

    if cache.get(cooldown_key):
        return stale_response()

    last_error = None
    for key in keys:
        try:
            r = requests.get(
                f"{AP_BASE}/{endpoint}",
                headers={"x-apisports-key": key},
                params=params,
                timeout=10,
            )
            if r.status_code in (401, 403, 429):
                last_error = requests.HTTPError(
                    f"API-Football returned HTTP {r.status_code}"
                )
                continue
            r.raise_for_status()
            data = r.json()
        except Exception as error:
            last_error = error
            continue

        errors = data.get("errors")
        if errors:
            print("API-Football error:", errors)
            last_error = ValueError(str(errors))
            continue

        cache.delete(cooldown_key)
        response = data.get("response", [])
        if response:
            cache.set(stale_key, response, 86400)
        return response

    if last_error:
        print("API-Football request failed:", last_error)
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
    cache_key = (
        "ap_live_matches" if settings.API_FOOTBALL_KEY
        else "football_data_live_matches"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if not settings.API_FOOTBALL_KEY:
        raw = FootballDataClient().get_live_matches(
            [info["code"] for info in TRACKED_LEAGUES.values()]
        )
        normalized = []
        for match in raw:
            fixture = _football_data_fixture(match)
            if fixture is None:
                continue
            short_status = fixture["fixture"]["status"]["short"]
            normalized.append({
                "id": fixture["fixture"]["id"],
                "league_id": fixture["league"]["id"],
                "league_name": fixture["league"]["name"],
                "league_logo": fixture["league"]["logo"],
                "home_team": fixture["teams"]["home"],
                "away_team": fixture["teams"]["away"],
                "home_score": fixture["goals"]["home"] or 0,
                "away_score": fixture["goals"]["away"] or 0,
                "status": "ht" if short_status == "HT" else "live",
                "display_minute": "HT" if short_status == "HT" else "LIVE",
            })
        cache.set(cache_key, normalized, 60)
        return normalized

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
    cache.set(cache_key, normalized, 60)
    return normalized


def get_today_matches(league_id=None):
    """
    Fetches today's fixtures across ALL tracked leagues with a short live-safe cache.
    If today has 0 matches (e.g., quiet Monday), automatically fetches tomorrow's fixtures!
    """
    today_str = date.today().isoformat()
    if not settings.API_FOOTBALL_KEY:
        fixtures = _football_data_fixtures(
            today_str, today_str, league_id=league_id
        )
        if not fixtures and not league_id:
            last_day = str(date.today() + timedelta(days=14))
            fixtures = _football_data_fixtures(
                today_str, last_day
            )
        return fixtures

    filtered = get_fixtures_by_date(today_str, league_id=league_id)

    # Fallback to tomorrow's fixtures if today has 0 tracked matches
    if not filtered and not league_id:
        last_day = str(date.today() + timedelta(days=14))
        filtered = get_fixtures_between(today_str, last_day)

    return filtered


def get_league_standings(league_id=39, season=2026):
    """
    Standings for a league (cached 6 hours).
    """
    provider = "ap" if settings.API_FOOTBALL_KEY else "football_data"
    cache_key = f"{provider}_standings_{league_id}_{season}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if not settings.API_FOOTBALL_KEY:
        code = TRACKED_LEAGUES.get(league_id, {}).get("code")
        if not code:
            return []
        data = FootballDataClient().get_standings(code)
        tables = data.get("standings", [])
        table = next(
            (item for item in tables if item.get("type") == "TOTAL"),
            tables[0] if tables else None,
        )
        rows = []
        if table:
            for entry in table.get("table", []):
                team = entry.get("team") or {}
                rows.append({
                    "rank": entry.get("position", 0),
                    "team": {
                        "id": team.get("id"),
                        "name": team.get("name", ""),
                        "logo": team.get("crest") or "",
                    },
                    "all": {
                        "played": entry.get("playedGames", 0),
                        "win": entry.get("won", 0),
                        "draw": entry.get("draw", 0),
                        "lose": entry.get("lost", 0),
                        "goals": {
                            "for": entry.get("goalsFor", 0),
                            "against": entry.get("goalsAgainst", 0),
                        },
                    },
                    "goalsDiff": entry.get("goalDifference", 0),
                    "points": entry.get("points", 0),
                    "form": entry.get("form") or "",
                })
        cache.set(cache_key, rows, 21600)
        return rows

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
    provider = "ap" if settings.API_FOOTBALL_KEY else "football_data"
    cache_key = f"{provider}_teams_{league_id}_{season}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if not settings.API_FOOTBALL_KEY:
        code = TRACKED_LEAGUES.get(league_id, {}).get("code")
        if not code:
            return []
        teams = FootballDataClient().get_teams(code)
        normalized = [{
            "team": {
                "id": item.get("id"),
                "name": item.get("name", ""),
                "logo": item.get("crest") or "",
                "country": (item.get("area") or {}).get("name", ""),
                "founded": item.get("founded"),
            },
            "venue": {
                "name": item.get("venue") or "",
                "city": (item.get("area") or {}).get("name", ""),
            },
        } for item in teams]
        cache.set(cache_key, normalized, 86400)
        return normalized

    raw = _ap_get("teams", {"league": league_id, "season": season})
    cache.set(cache_key, raw, 86400)
    return raw


def get_top_scorers(league_id=39, season=2026):
    """Fetches top scorers/players for a league (cached 12 hours)."""
    provider = "ap" if settings.API_FOOTBALL_KEY else "football_data"
    cache_key = f"{provider}_topscorers_{league_id}_{season}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if not settings.API_FOOTBALL_KEY:
        code = TRACKED_LEAGUES.get(league_id, {}).get("code")
        if not code:
            return []
        scorers = FootballDataClient().get_scorers(code)
        normalized = []
        for item in scorers:
            player = item.get("player") or {}
            team = item.get("team") or {}
            normalized.append({
                "player": {
                    "id": player.get("id"),
                    "name": player.get("name", ""),
                    "photo": "",
                    "nationality": player.get("nationality", ""),
                    "age": None,
                },
                "statistics": [{
                    "team": {
                        "id": team.get("id"),
                        "name": team.get("name", ""),
                        "logo": team.get("crest") or "",
                    },
                    "games": {"appearences": item.get("playedMatches", 0)},
                    "goals": {
                        "total": item.get("goals", 0),
                        "assists": item.get("assists", 0),
                    },
                }],
            })
        cache.set(cache_key, normalized, 21600)
        return normalized

    raw = _ap_get("players/topscorers", {"league": league_id, "season": season})
    cache.set(cache_key, raw, 43200)
    return raw
def get_fixtures_by_date(date_str, league_id=None):
    """
    Fetches fixtures for a specific YYYY-MM-DD date across all tracked leagues.
    """
    if not settings.API_FOOTBALL_KEY:
        return _football_data_fixtures(
            date_str, date_str, league_id=league_id
        )

    cache_key = f"ap_fixtures_date_{date_str}"
    cached = cache.get(cache_key)
    if cached is None:
        raw = _ap_get("fixtures", {"date": date_str})
        cached = [m for m in raw if m["league"]["id"] in TRACKED_LEAGUES]
        cached.sort(key=lambda m: (
            TRACKED_LEAGUES[m["league"]["id"]]["priority"],
            m["fixture"]["timestamp"],
        ))
        cache.set(cache_key, cached, 180)

    if league_id:
        return [m for m in cached if m["league"]["id"] == league_id]
    return cached


def get_fixtures_between(date_from, date_to, league_id=None):
    """Fetch a date range of tracked fixtures for empty-day fallbacks."""
    if not settings.API_FOOTBALL_KEY:
        return _football_data_fixtures(
            date_from, date_to, league_id=league_id
        )

    raw = _ap_get("fixtures", {"from": date_from, "to": date_to})
    fixtures = [match for match in raw if match["league"]["id"] in TRACKED_LEAGUES]
    if league_id:
        fixtures = [
            match for match in fixtures
            if match["league"]["id"] == league_id
        ]
    fixtures.sort(key=lambda match: (
        TRACKED_LEAGUES[match["league"]["id"]]["priority"],
        match["fixture"]["timestamp"],
    ))
    return fixtures


def get_fixture_full_details(fixture_id):
    """
    Combines fixture, event, lineup, statistics and player-rating data for the match center.
    """
    provider = "ap" if settings.API_FOOTBALL_KEY else "football_data"
    cache_key = f"{provider}_fixture_full_{fixture_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if not settings.API_FOOTBALL_KEY:
        match = FootballDataClient().get_match(fixture_id)
        fixture = _football_data_fixture(match)
        if fixture is None:
            return {}
        score = match.get("score") or {}
        half_time = score.get("halfTime") or {}
        fixture["goals"] = score.get("fullTime") or {}
        home_team = fixture["teams"]["home"]
        away_team = fixture["teams"]["away"]
        events = []
        previous_score = {"home": 0, "away": 0}
        goal_type_labels = {
            "REGULAR": "Normal Goal",
            "PENALTY": "Penalty",
            "OWN_GOAL": "Own Goal",
        }
        for goal in match.get("goals") or []:
            goal_score = goal.get("score") or {}
            home_after = goal_score.get("home", previous_score["home"])
            away_after = goal_score.get("away", previous_score["away"])
            event_team = (
                home_team if home_after > previous_score["home"]
                else away_team if away_after > previous_score["away"]
                else goal.get("team") or {}
            )
            events.append({
                "type": "Goal",
                "detail": goal_type_labels.get(
                    goal.get("type"), goal.get("type", "Goal")
                ),
                "time": {
                    "elapsed": goal.get("minute"),
                    "extra": goal.get("injuryTime"),
                },
                "team": event_team,
                "player": goal.get("scorer") or {},
                "assist": goal.get("assist") or {},
            })
            previous_score = {"home": home_after, "away": away_after}
        fixture["events"] = events
        fixture["lineups"] = []
        fixture["statistics"] = []
        fixture["players"] = []
        fixture["score"] = {
            "halfTime": half_time,
            "fullTime": score.get("fullTime") or {},
        }
        cache.set(cache_key, fixture, 60)
        return fixture

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
