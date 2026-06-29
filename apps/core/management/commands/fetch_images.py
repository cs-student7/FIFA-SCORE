"""
Management command to bulk-download country flags and league/competition logos
from free public sources, and attach them to existing Country/Competition records.

Usage:
    python manage.py fetch_images            # fetch both flags and logos
    python manage.py fetch_images --flags     # only country flags
    python manage.py fetch_images --logos     # only league logos
"""
import time

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.teams.models import Country
from apps.leagues.models import Competition

try:
    import pycountry
except ImportError:
    pycountry = None


class Command(BaseCommand):
    help = "Bulk-fetch country flags and league logos from free online sources."

    # Common league name aliases -> name as stored in TheSportsDB
    LEAGUE_ALIASES = {
        'premier league': 'english premier league',
        'la liga': 'spanish la liga',
        'bundesliga': 'german bundesliga',
        'serie a': 'italian serie a',
        'fa cup': 'english fa cup',
        'uefa champions league': 'uefa champions league',
        'ligue 1': 'french ligue 1',
        'eredivisie': 'dutch eredivisie',
        'primeira liga': 'portuguese primeira liga',
        'mls': 'american major league soccer',
    }

    def add_arguments(self, parser):
        parser.add_argument('--flags', action='store_true', help='Only fetch country flags')
        parser.add_argument('--logos', action='store_true', help='Only fetch league logos')
        parser.add_argument('--overwrite', action='store_true', help='Re-download even if already set')

    def handle(self, *args, **options):
        do_flags = options['flags'] or not options['logos']
        do_logos = options['logos'] or not options['flags']
        overwrite = options['overwrite']

        if do_flags:
            self.fetch_flags(overwrite)
        if do_logos:
            self.fetch_logos(overwrite)

    # ------------------------------------------------------------------ #
    # Country flags via flagcdn.com (needs ISO alpha-2 code)
    # ------------------------------------------------------------------ #
    def fetch_flags(self, overwrite):
        if pycountry is None:
            self.stderr.write(self.style.ERROR(
                "pycountry is not installed. Run: pip install pycountry"
            ))
            return

        self.stdout.write("Fetching country flags...")
        countries = Country.objects.all()
        if not overwrite:
            countries = countries.filter(flag='')

        success, failed = 0, []

        for country in countries:
            alpha2 = self._resolve_alpha2(country.name, country.code)
            if not alpha2:
                failed.append(country.name)
                continue

            url = f"https://flagcdn.com/w320/{alpha2.lower()}.png"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200 and resp.content:
                    filename = f"{alpha2.lower()}.png"
                    country.flag.save(filename, ContentFile(resp.content), save=True)
                    success += 1
                    self.stdout.write(f"  OK  {country.name} ({alpha2})")
                else:
                    failed.append(country.name)
            except requests.RequestException:
                failed.append(country.name)

            time.sleep(0.1)

        self.stdout.write(self.style.SUCCESS(f"Flags done: {success} succeeded."))
        if failed:
            self.stdout.write(self.style.WARNING(f"Failed to match/fetch: {', '.join(failed)}"))

    def _resolve_alpha2(self, name, existing_code):
        if existing_code and len(existing_code) == 2:
            return existing_code
        try:
            matches = pycountry.countries.search_fuzzy(name)
            if matches:
                return matches[0].alpha_2
        except LookupError:
            pass
        return None

    # ------------------------------------------------------------------ #
    # League/competition logos via TheSportsDB free API
    # ------------------------------------------------------------------ #
    def fetch_logos(self, overwrite):
        self.stdout.write("Fetching league logos...")
        competitions = Competition.objects.all()
        if not overwrite:
            competitions = competitions.filter(logo='')

        success, failed = 0, []

        try:
            resp = requests.get(
                "https://www.thesportsdb.com/api/v1/json/3/search_all_leagues.php",
                params={'s': 'Soccer'},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            # NOTE: TheSportsDB misspells this key as "countrys" (not "countries")
            all_leagues = data.get('countrys') or data.get('countries') or []
        except (requests.RequestException, ValueError):
            self.stderr.write(self.style.ERROR("Could not reach TheSportsDB API."))
            return

        if not all_leagues:
            self.stderr.write(self.style.ERROR(
                "TheSportsDB returned no league data — API may be down or response format changed."
            ))
            return

        lookup = {}
        for entry in all_leagues:
            league_name = (entry.get('strLeague') or '').lower()
            badge = entry.get('strBadge') or entry.get('strLogo')
            if league_name and badge:
                lookup[league_name] = badge

        for comp in competitions:
            search_name = comp.name.lower()
            search_name = self.LEAGUE_ALIASES.get(search_name, search_name)

            badge_url = lookup.get(search_name)
            if not badge_url:
                for league_name, badge in lookup.items():
                    if search_name in league_name or league_name in search_name:
                        badge_url = badge
                        break

            if not badge_url:
                failed.append(comp.name)
                continue

            try:
                img_resp = requests.get(badge_url, timeout=10)
                if img_resp.status_code == 200 and img_resp.content:
                    ext = badge_url.split('.')[-1][:4]
                    filename = f"{comp.slug}.{ext}"
                    comp.logo.save(filename, ContentFile(img_resp.content), save=True)
                    success += 1
                    self.stdout.write(f"  OK  {comp.name}")
                else:
                    failed.append(comp.name)
            except requests.RequestException:
                failed.append(comp.name)

            time.sleep(0.2)

        self.stdout.write(self.style.SUCCESS(f"Logos done: {success} succeeded."))
        if failed:
            self.stdout.write(self.style.WARNING(f"No match found for: {', '.join(failed)}"))