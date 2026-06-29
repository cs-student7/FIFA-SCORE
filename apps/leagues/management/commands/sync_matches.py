from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, is_naive

from apps.core.services.football_data import FootballDataClient
from apps.leagues.models import Competition
from apps.matches.models import Match
from apps.teams.models import Team

STATUS_MAP = {
    "SCHEDULED": "scheduled",
    "TIMED": "scheduled",
    "IN_PLAY": "live",
    "PAUSED": "ht",
    "FINISHED": "ft",
    "POSTPONED": "postponed",
    "SUSPENDED": "cancelled",
    "CANCELLED": "cancelled",
    "AWARDED": "ft",
}


class Command(BaseCommand):
    help = "Sync fixtures and results from football-data.org"

    def add_arguments(self, parser):
        parser.add_argument(
            "--codes", nargs="*", default=None,
            help="Limit to specific competition codes; default = every synced competition",
        )
        parser.add_argument(
            "--status", default=None,
            help="Optional football-data.org status filter, e.g. SCHEDULED, FINISHED, LIVE",
        )

    def handle(self, *args, **options):
        client = FootballDataClient()
        qs = Competition.objects.exclude(api_code="")
        if options["codes"]:
            qs = qs.filter(api_code__in=options["codes"])

        for comp in qs:
            season = comp.seasons.filter(is_current=True).first()
            if not season:
                self.stdout.write(self.style.WARNING(f"Skipping {comp.name}: no current season"))
                continue

            self.stdout.write(f"Syncing matches for {comp.name}...")
            try:
                matches = client.get_matches(comp.api_code, status=options["status"])
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  Failed to fetch matches: {exc}"))
                continue

            count = 0
            for m in matches:
                if self.sync_match(m, season):
                    count += 1
            self.stdout.write(self.style.SUCCESS(f"  -> synced {count} matches"))

    def sync_match(self, data, season):
        home = Team.objects.filter(api_id=data["homeTeam"]["id"]).first()
        away = Team.objects.filter(api_id=data["awayTeam"]["id"]).first()
        if not home or not away:
            return False

        kickoff = datetime.strptime(data["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
        if is_naive(kickoff):
            kickoff = make_aware(kickoff)

        score = data.get("score") or {}
        full_time = score.get("fullTime") or {}
        half_time = score.get("halfTime") or {}

        Match.objects.update_or_create(
            api_id=data["id"],
            defaults={
                "season": season,
                "home_team": home,
                "away_team": away,
                "kickoff": kickoff,
                "status": STATUS_MAP.get(data.get("status"), "scheduled"),
                "home_score": full_time.get("home") or 0,
                "away_score": full_time.get("away") or 0,
                "home_ht_score": half_time.get("home"),
                "away_ht_score": half_time.get("away"),
                "matchday": data.get("matchday"),
                "venue": data.get("venue") or "",
            },
        )
        return True