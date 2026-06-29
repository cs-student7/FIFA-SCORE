import time
import random
from django.core.management.base import BaseCommand
from apps.matches.models import Match, MatchEvent


class Command(BaseCommand):
    help = 'Simulates live match updates every 30 seconds'

    def handle(self, *args, **options):
        self.stdout.write('🔴 Simulating live matches... Press Ctrl+C to stop\n')

        while True:
            live_matches = Match.objects.filter(status='live').select_related(
                'home_team', 'away_team'
            )

            if not live_matches.exists():
                self.stdout.write('No live matches found.')
            
            for match in live_matches:
                old_min = match.minute or 0
                match.minute = min(old_min + 1, 90)

                # Random goal (5% chance each tick)
                if random.random() < 0.05:
                    scorer_team = random.choice(['home', 'away'])
                    if scorer_team == 'home':
                        match.home_score += 1
                        team = match.home_team
                    else:
                        match.away_score += 1
                        team = match.away_team

                    MatchEvent.objects.create(
                        match=match,
                        event_type='goal',
                        minute=match.minute,
                        team=team,
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f'⚽ GOAL! {team.name} — '
                        f'{match.home_team.short_name} {match.home_score}–'
                        f'{match.away_score} {match.away_team.short_name} '
                        f'({match.minute}\')'
                    ))

                # End match at 90 minutes
                if match.minute >= 90:
                    match.status = 'ft'
                    match.period = 'fin'
                    self.stdout.write(f'🏁 FT: {match.home_team} {match.home_score}–{match.away_score} {match.away_team}')

                match.save()

            self.stdout.write(f'⏱  Tick — {live_matches.count()} live matches updated')
            time.sleep(30)