from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.core.services.football_data import (
    FootballDataClient, FEATURED_COMPETITIONS, download_image,
)
from apps.leagues.models import Competition, Season
from apps.teams.models import Country


class Command(BaseCommand):
    help = "Sync competitions (leagues), their country, and current season from football-data.org"

    def add_arguments(self, parser):
        parser.add_argument(
            "--codes", nargs="*", default=FEATURED_COMPETITIONS,
            help="football-data.org competition codes, e.g. PL BL1 PD SA CL",
        )

    def handle(self, *args, **options):
        client = FootballDataClient()
        for code in options["codes"]:
            self.stdout.write(f"Fetching competition {code}...")
            try:
                data = client.get_competition(code)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  Failed for {code}: {exc}"))
                continue
            self.sync_competition(data, code)

    def sync_competition(self, data, code):
        area = data.get("area", {})
        country = None
        if area.get("name") and area.get("name") != "World":
            country, _ = Country.objects.update_or_create(
                api_code=area.get("code") or "",
                defaults={"name": area.get("name")},
            )
            if not country.flag:
                flag_file = download_image(area.get("flag"))
                if flag_file:
                    country.flag.save(flag_file.name, flag_file, save=True)

        comp, created = Competition.objects.update_or_create(
            api_code=code,
            defaults={
                "name": data.get("name"),
                "short_name": code,
                "slug": slugify(data.get("name")),
                "country": country,
                "comp_type": "league" if country else "international",
                "is_featured": code in FEATURED_COMPETITIONS,
                "is_active": True,
            },
        )
        if not comp.logo:
            logo_file = download_image(data.get("emblem"))
            if logo_file:
                comp.logo.save(logo_file.name, logo_file, save=True)

        season_data = data.get("currentSeason")
        if season_data:
            start = datetime.strptime(season_data["startDate"], "%Y-%m-%d").date()
            end = datetime.strptime(season_data["endDate"], "%Y-%m-%d").date()
            name = f"{start.year}/{str(end.year)[2:]}" if start.year != end.year else str(start.year)
            Season.objects.filter(competition=comp).update(is_current=False)
            Season.objects.update_or_create(
                competition=comp, name=name,
                defaults={"start_date": start, "end_date": end, "is_current": True},
            )

        self.stdout.write(self.style.SUCCESS(
            f"  -> {comp.name} ({'created' if created else 'updated'})"
        ))