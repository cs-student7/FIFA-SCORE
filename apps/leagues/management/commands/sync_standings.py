from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.core.services.football_data import FootballDataClient, download_image
from apps.leagues.models import Competition, Standing
from apps.teams.models import Country, Team


class Command(BaseCommand):
    help = "Sync teams (with crest + country) and the league table from football-data.org"

    def add_arguments(self, parser):
        parser.add_argument(
            "--codes", nargs="*", default=None,
            help="Limit to specific competition codes; default = every synced competition",
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

            self.stdout.write(f"Syncing teams for {comp.name}...")
            try:
                teams_data = client.get_teams(comp.api_code)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  Failed to fetch teams: {exc}"))
                continue
            for team_data in teams_data:
                self.sync_team(team_data)

            self.stdout.write(f"Syncing standings for {comp.name}...")
            try:
                standings_data = client.get_standings(comp.api_code)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  Failed to fetch standings: {exc}"))
                continue
            self.sync_standings(standings_data, season)
            self.stdout.write(self.style.SUCCESS("  -> done"))

    def sync_team(self, data):
        country = None
        area = data.get("area") or {}
        if area.get("name"):
            country, _ = Country.objects.update_or_create(
                api_code=area.get("code") or "",
                defaults={"name": area.get("name")},
            )
            if not country.flag:
                flag_file = download_image(area.get("flag"))
                if flag_file:
                    country.flag.save(flag_file.name, flag_file, save=True)

        team, _created = Team.objects.update_or_create(
            api_id=data.get("id"),
            defaults={
                "name": data.get("name"),
                "short_name": (data.get("shortName") or data.get("tla") or "")[:50],
                "slug": slugify(data.get("name")),
                "country": country,
                "founded": data.get("founded"),
                "stadium": data.get("venue") or "",
                "website": data.get("website") or "",
            },
        )
        if not team.logo:
            logo_file = download_image(data.get("crest"))
            if logo_file:
                team.logo.save(logo_file.name, logo_file, save=True)
        return team

    def sync_standings(self, data, season):
        tables = data.get("standings", [])
        total_table = next((t for t in tables if t.get("type") == "TOTAL"), tables[0] if tables else None)
        if not total_table:
            return

        for row in total_table.get("table", []):
            team = Team.objects.filter(api_id=row["team"]["id"]).first()
            if not team:
                continue
            Standing.objects.update_or_create(
                season=season, team=team,
                defaults={
                    "position": row.get("position", 0),
                    "played": row.get("playedGames", 0),
                    "won": row.get("won", 0),
                    "drawn": row.get("draw", 0),
                    "lost": row.get("lost", 0),
                    "goals_for": row.get("goalsFor", 0),
                    "goals_against": row.get("goalsAgainst", 0),
                    "points": row.get("points", 0),
                    "form": (row.get("form") or "").replace(",", ""),
                },
            )