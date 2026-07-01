

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


=======
# FIFA-SCORE
FIFA Score is a Django-based football web application that delivers live match scores, fixtures, league standings, and team statistics for major international tournaments and European leagues. Built with real-time API integration and a responsive, user-friendly interface.
