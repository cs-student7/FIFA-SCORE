# LeaguePulse

LeaguePulse is a Django football scores and statistics site. It uses API-Football
(API-Sports) for tracked-league fixtures, match events, statistics, lineups,
player ratings, and standings.

## Configuration

Set these values in the deployment environment or a local, untracked `.env`
file. Never commit API keys, database passwords, or Redis URLs.

| Variable | Required | Purpose |
| --- | --- | --- |
| `API_FOOTBALL_KEY` | For live football data | API-Football subscription key |
| `API_FOOTBALL_URL` | No | API base URL; defaults to `https://v3.football.api-sports.io` |
| `API_TOKEN` | No | Bearer token for the World Cup API (`WC_API_TOKEN` remains a legacy fallback) |
| `FIVE_DOLLAR_API_KEY` | No | Primary 5DollarFootballAPI key for fixture fallback |
| `FIVE_DOLLAR_API_KEY_2` | No | Secondary key, tried after authorization or rate-limit failures |
| `DATABASE_URL` | Production | Persistent PostgreSQL database URL; SQLite is used when unset |
| `REDIS_URL` | Recommended for multi-worker deployments | Shared cache, Channels layer, and Celery broker |
| `SECRET_KEY` | Production | Django secret key |
| `DEBUG` | Production | Set to `False` |
| `ALLOWED_HOSTS` | Production | Comma-separated hostnames |

The site keeps a local file cache when `REDIS_URL` is unset. That is suitable
for development or a single process, but production workers should share Redis
so they use the same provider cache and live updates. Live scores refresh from
the provider on a short cache interval to limit API usage. When configured, the
5DollarFootballAPI keys provide same-day and upcoming scheduled fixture
fallback, with the second key used after an authorization or rate-limit response.
Match ratings, lineups, and statistics are displayed when the provider plan supplies them;
coverage varies by competition and match.

## Run locally

Install `requirements.txt`, configure `API_FOOTBALL_KEY` in `.env`, then run:

```powershell
python manage.py migrate
python manage.py runserver
```
