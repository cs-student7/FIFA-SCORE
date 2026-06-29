import requests
from django.conf import settings
from django.core.cache import cache
from datetime import date, datetime

# ── api-sports.io ─────────────────────────────────────────────
AP_HEADERS = {"x-apisports-key": settings.API_FOOTBALL_KEY}
AP_BASE    = "https://v3.football.api-sports.io"

# ── World Cup 2026 API ────────────────────────────────────────
WC_BASE    = "http://worldcup26.ir:3050"

def _ap_get(endpoint, params=None):
    try:
        r = requests.get(f"{AP_BASE}/{endpoint}",
                        headers=AP_HEADERS,
                        params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("response", [])
    except Exception:
        return []

def _wc_get(endpoint):
    """Call WC API with JWT token. Retries once, falls back to stale cache."""
    token = settings.WC_API_TOKEN
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    for attempt in range(2):
        try:
            r = requests.get(f"{WC_BASE}/{endpoint}",
                            headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
            cache.set(f'stale_{endpoint}', data, 60*60*24)
            return data
        except Exception:
            if attempt == 0:
                continue  # try once more immediately
            stale = cache.get(f'stale_{endpoint}')
            return stale if stale else {}
    return {}

# ── api-sports functions ───────────────────────────────────────
def get_live_matches():
    return _ap_get("fixtures", {"live": "all"})

def get_today_matches(league_id=None):
    params = {"date": str(date.today())}
    if league_id:
        params["league"] = league_id
    return _ap_get("fixtures", params)

def get_match_events(fixture_id):
    return _ap_get("fixtures/events", {"fixture": fixture_id})

def get_match_lineups(fixture_id):
    return _ap_get("fixtures/lineups", {"fixture": fixture_id})

def get_match_stats(fixture_id):
    return _ap_get("fixtures/statistics", {"fixture": fixture_id})

# ── World Cup 2026 ─────────────────────────────────────────────
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
    # API returns {"games": [...]}
    matches = data.get("games", []) if isinstance(data, dict) else []
    cache.set('wc_all_matches', matches, 60)
    return matches

def _build_team_names():
    """Build team_id → name dict from all games."""
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
    return [g for g in games
            if str(g.get("time_elapsed","")).lower()
               not in ["finished","notstarted",""]
            and str(g.get("finished","")).upper() != "TRUE"]

def get_wc_today_matches():
    games = get_wc_all_matches()
    today = date.today()
    result = []
    for g in games:
        dt = _parse_date(g.get("local_date",""))
        if dt and dt.date() == today:
            result.append(g)
    return result

def get_wc_upcoming():
    return [g for g in get_wc_today_matches()
            if str(g.get("time_elapsed","")).lower() == "notstarted"]

def get_wc_results():
    games = get_wc_all_matches()
    finished = [g for g in games
                if str(g.get("finished","")).upper() == "TRUE"]
    finished.sort(
        key=lambda g: _parse_date(g.get("local_date","")) or datetime.min,
        reverse=True
    )
    return finished[:20]

def get_wc_groups():
    """Group standings enriched with team names."""
    cached = cache.get('wc_groups_enriched')
    if cached is not None:
        return cached

    groups_raw = _wc_get("get/groups")
    team_names = _build_team_names()

    # handle both list and dict response
    if isinstance(groups_raw, dict):
        groups_list = (groups_raw.get("groups") or
                      groups_raw.get("data") or [])
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
                continue  # skip unknown teams
            enriched.append({
                "name": name,
                "mp":   int(team.get("mp", 0)),
                "w":    int(team.get("w",  0)),
                "d":    int(team.get("d",  0)),
                "l":    int(team.get("l",  0)),
                "pts":  int(team.get("pts",0)),
                "gf":   int(team.get("gf", 0)),
                "ga":   int(team.get("ga", 0)),
                "gd":   int(team.get("gd", 0)),
            })
        enriched.sort(
            key=lambda t: (t["pts"], t["gd"], t["gf"]),
            reverse=True
        )
        if enriched:  # only add groups that have known teams
            result.append({
                "name":  group.get("name", ""),
                "teams": enriched,
            })

    cache.set('wc_groups_enriched', result, 120)
    return result