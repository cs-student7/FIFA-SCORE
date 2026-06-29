# ⚽ GoalPulse — Live Football Score Platform

A full-featured Django football scores platform using **SQLite** (zero-config, no PostgreSQL/Redis needed).

## Quick Start

```bash
# 1. Create & activate virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run database migrations
python manage.py migrate

# 4. Seed with demo data
python manage.py seed_data

# 5. Start the server
python manage.py runserver
```

Visit **http://127.0.0.1:8000** — that's it!

## Seed options

```bash
python manage.py seed_data --live 5    # 5 live matches
python manage.py seed_data --clear     # wipe and re-seed
```

Admin login (created automatically by seed_data): **admin / admin123**  
Admin panel: http://127.0.0.1:8000/admin/

## Pages

| URL | Description |
|-----|-------------|
| `/` | Home – live, upcoming, results, standings |
| `/matches/` | All fixtures by date |
| `/matches/<id>/` | Match detail with stats & momentum chart |
| `/leagues/` | All competitions |
| `/leagues/<slug>/` | League table, scorers, fixtures |
| `/teams/` | Team directory |
| `/teams/<slug>/` | Team detail with squad & recent matches |
| `/players/` | Player directory |
| `/players/<slug>/` | Player profile |
| `/accounts/login/` | Sign in |
| `/accounts/register/` | Create account |
| `/admin/` | Django admin |

## REST API

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/matches/live/` | Live matches |
| `GET /api/v1/matches/?date=YYYY-MM-DD` | Matches by date |
| `GET /api/v1/matches/<id>/` | Match detail |
| `GET /api/v1/matches/<id>/stats/` | Match statistics |
| `GET /api/v1/matches/<id>/momentum/` | Momentum data |
| `GET /api/v1/leagues/` | All competitions |
| `GET /api/v1/leagues/standings/<season_id>/` | Standings |
| `GET /api/v1/leagues/top-scorers/<season_id>/` | Top scorers |
| `GET /api/v1/teams/` | All teams |
| `GET /api/v1/players/` | All players |
| `GET /api/v1/search/?q=query` | Global search |

## Tech Stack

- **Django 5** + SQLite (zero-config database)
- **Django REST Framework** — JSON API
- **Bootstrap 5** dark theme + custom CSS
- **Chart.js** — momentum chart
- Live updates via **polling** (no WebSocket/Redis needed)



  ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
    'anon': '1000/hour',
    'user': '10000/hour',
},