# LeaguePulse

LeaguePulse is a Django football scores and statistics site. It uses API-Football
(API-Sports) for tracked-league fixtures, match events, statistics, lineups,
player ratings, and standings.

## Configuration

Set these values in the deployment environment or a local, untracked `.env`
file. Never commit API keys, database passwords, or Redis URLs.

| Variable | Required | Purpose |
| --- | --- | --- |
| `API_FOOTBALL_KEY` | No | Optional API-Football subscription key; used when configured |
| `API_FOOTBALL_URL` | No | API base URL; defaults to `https://v3.football.api-sports.io` |
| `API_TOKEN` | For football-data.org pages | X-Auth-Token for football-data.org v4 |
| `WC_API_TOKEN` | No | Bearer token for the World Cup API |
| `DATABASE_URL` | Production | Persistent PostgreSQL database URL; SQLite is used when unset |
| `REDIS_URL` | Recommended for multi-worker deployments | Shared cache, Channels layer, and Celery broker |
| `SECRET_KEY` | Production | Django secret key |
| `DEBUG` | Production | Set to `False` |
| `ALLOWED_HOSTS` | Production | Comma-separated hostnames |

The site keeps a local file cache when `REDIS_URL` is unset. That is suitable
for development or a single process, but production workers should share Redis
so they use the same provider cache and live updates. When `API_FOOTBALL_KEY`
is not configured, match fixtures, standings, teams, and scorers use
football-data.org v4 with `API_TOKEN`. Results are cached to limit API usage.
Match ratings, lineups, and statistics depend on the configured provider and
its competition coverage.

## Run locally

Install `requirements.txt`, configure `API_FOOTBALL_KEY` in `.env`, then run:

```powershell
python manage.py migrate
python manage.py runserver
```
