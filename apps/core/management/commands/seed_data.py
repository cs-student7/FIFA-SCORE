"""
Management command: python manage.py seed_data
Populates the SQLite database with realistic demo football data.
Usage:
  python manage.py seed_data            # default 3 live matches
  python manage.py seed_data --live 5  # 5 live matches
  python manage.py seed_data --clear   # wipe and re-seed
"""
import random
from datetime import timedelta, date
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.teams.models import Country, Team
from apps.leagues.models import Competition, Season, Standing
from apps.players.models import Player
from apps.matches.models import Match, MatchStatistic, MatchEvent, MatchMomentum, TopScorer
from django.contrib.auth.models import User

COUNTRIES = [
    ('England', 'ENG'), ('Spain', 'ESP'), ('Germany', 'GER'),
    ('Italy', 'ITA'), ('France', 'FRA'), ('Portugal', 'POR'),
    ('Netherlands', 'NED'), ('Brazil', 'BRA'), ('Argentina', 'ARG'),
    ('Norway', 'NOR'), ('Belgium', 'BEL'), ('Croatia', 'CRO'),
]

COMPETITIONS = [
    ('Premier League',       'PL',  'ENG', 'league',        1, True),
    ('La Liga',              'LL',  'ESP', 'league',        1, True),
    ('Bundesliga',           'BL',  'GER', 'league',        1, True),
    ('Serie A',              'SA',  'ITA', 'league',        1, True),
    ('Ligue 1',              'L1',  'FRA', 'league',        1, False),
    ('UEFA Champions League','UCL', None,  'international', 1, True),
    ('FA Cup',               'FAC', 'ENG', 'cup',           1, False),
]

EPL_TEAMS = [
    ('Manchester City',   'Man City',  '#6CABDD', '#1C2C5B', 'Etihad Stadium',               55097, 1880),
    ('Arsenal',           'Arsenal',   '#EF0107', '#FFFFFF', 'Emirates Stadium',              60704, 1886),
    ('Liverpool',         'Liverpool', '#C8102E', '#F6EB61', 'Anfield',                       54074, 1892),
    ('Chelsea',           'Chelsea',   '#034694', '#FFFFFF', 'Stamford Bridge',               40341, 1905),
    ('Manchester United', 'Man Utd',   '#DA291C', '#FBE122', 'Old Trafford',                  74140, 1878),
    ('Tottenham Hotspur', 'Spurs',     '#132257', '#FFFFFF', 'Tottenham Hotspur Stadium',     62850, 1882),
    ('Newcastle United',  'Newcastle', '#241F20', '#FFFFFF', "St. James' Park",               52305, 1892),
    ('Aston Villa',       'Aston Villa','#95BFE5','#670E36', 'Villa Park',                    42785, 1874),
    ('Brighton',          'Brighton',  '#0057B8', '#FFCD00', 'Amex Stadium',                  31800, 1901),
    ('West Ham',          'West Ham',  '#7A263A', '#1BB1E7', 'London Stadium',                60000, 1895),
    ('Brentford',         'Brentford', '#E30613', '#FFFFFF', 'Gtech Community Stadium',       17250, 1889),
    ('Fulham',            'Fulham',    '#CC0000', '#FFFFFF', 'Craven Cottage',                25700, 1879),
    ('Crystal Palace',    'C. Palace', '#1B458F', '#C4122E', 'Selhurst Park',                 25486, 1905),
    ('Wolves',            'Wolves',    '#FDB913', '#231F20', 'Molineux',                      32050, 1877),
    ('Nottm Forest',      'Forest',    '#DD0000', '#FFFFFF', 'City Ground',                   30445, 1865),
    ('Everton',           'Everton',   '#003399', '#FFFFFF', 'Goodison Park',                 39414, 1878),
    ('Bournemouth',       'Bournemouth','#DA291C','#000000', 'Vitality Stadium',              11364, 1899),
    ('Sheffield Utd',     'Sheff Utd', '#EE2737', '#FFFFFF', 'Bramall Lane',                  32050, 1889),
    ('Burnley',           'Burnley',   '#6C1D45', '#99D6EA', 'Turf Moor',                     21944, 1882),
    ('Luton Town',        'Luton',     '#F78F1E', '#FFFFFF', 'Kenilworth Road',               10356, 1885),
]

LA_LIGA_TEAMS = [
    ('Real Madrid',    'R. Madrid', '#FEBE10', '#FFFFFF', 'Santiago Bernabéu',  81044, 1902),
    ('Barcelona',      'Barça',     '#A50044', '#004D98', 'Spotify Camp Nou',   99354, 1899),
    ('Atletico Madrid','Atletico',  '#CB3524', '#FFFFFF', 'Civitas Metropolitano',68456,1903),
    ('Real Sociedad',  'R. Sociedad','#0166AB', '#FFFFFF', 'Reale Arena',        39500, 1909),
    ('Athletic Club',  'Athletic',  '#EE2523', '#FFFFFF', 'San Mamés',          53289, 1898),
    ('Villarreal',     'Villarreal','#FFE135', '#005F9E', 'Estadio de la Cerámica',23500,1923),
]

POSITIONS = ['GK', 'CB', 'CB', 'LB', 'RB', 'DM', 'CM', 'CM', 'AM', 'LW', 'RW', 'ST', 'CF',
             'GK', 'CB', 'LB', 'RB', 'CM', 'AM', 'ST', 'CF']
FIRST_NAMES = [
    'James','Liam','Noah','Oliver','Lucas','Mason','Ethan','Henry','Sebastian',
    'Mohamed','Erling','Kylian','Vinicius','Pedri','Jude','Phil','Marcus','Bukayo',
    'Trent','Declan','Rodri','Bruno','Kevin','Robert','Lionel','Cristiano','Neymar',
    'Raheem','Leroy','Thomas','Kai','Jack','Ivan','Lautaro','Antoine','Ousmane',
]
LAST_NAMES = [
    'Smith','Johnson','Williams','Jones','Brown','Davis','Garcia','Wilson',
    'Martinez','Anderson','Taylor','Thomas','Hernandez','Moore','Jackson',
    'Haaland','Mbappe','Bellingham','Saka','Rice','Foden','Salah','De Bruyne',
    'Fernandes','Alexander-Arnold','Rodri','Vinicius','Pedri','Gavi','Camavinga',
    'Musiala','Wirtz','Bellingham','Valverde','Tchouameni','Diaz','Nunez',
]
REFEREES = [
    'Michael Oliver','Anthony Taylor','Craig Pawson','Stuart Attwell',
    'Paul Tierney','Chris Kavanagh','Simon Hooper','Andy Madley',
    'Mateu Lahoz','Felix Zwayer','Clement Turpin','Daniele Orsato',
]


class Command(BaseCommand):
    help = 'Seeds the SQLite database with demo football data'

    def add_arguments(self, parser):
        parser.add_argument('--live', type=int, default=3,
                            help='Number of live matches to create (default: 3)')
        parser.add_argument('--clear', action='store_true',
                            help='Clear existing data before seeding')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('⚠  Clearing existing data...')
            MatchMomentum.objects.all().delete()
            MatchEvent.objects.all().delete()
            MatchStatistic.objects.all().delete()
            Match.objects.all().delete()
            TopScorer.objects.all().delete()
            Standing.objects.all().delete()
            Season.objects.all().delete()
            Competition.objects.all().delete()
            Player.objects.all().delete()
            Team.objects.all().delete()
            Country.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        # ── Countries ──────────────────────────────────────────
        self.stdout.write('Creating countries...')
        countries = {}
        for name, code in COUNTRIES:
            c, _ = Country.objects.get_or_create(code=code, defaults={'name': name})
            countries[code] = c

        # ── Competitions ───────────────────────────────────────
        self.stdout.write('Creating competitions...')
        competitions = {}
        for name, short, country_code, ctype, tier, featured in COMPETITIONS:
            slug = slugify(name)
            country = countries.get(country_code) if country_code else None
            comp, _ = Competition.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name, 'short_name': short, 'country': country,
                    'tier': tier, 'is_featured': featured, 'comp_type': ctype,
                }
            )
            competitions[short] = comp

        # ── EPL Teams ──────────────────────────────────────────
        self.stdout.write('Creating EPL teams...')
        eng = countries['ENG']
        epl_teams = []
        for name, short, pc, sc, stadium, cap, founded in EPL_TEAMS:
            team, _ = Team.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    'name': name, 'short_name': short, 'country': eng,
                    'primary_color': pc, 'secondary_color': sc,
                    'stadium': stadium, 'stadium_capacity': cap, 'founded': founded,
                    'city': stadium.split()[-1] if stadium else '',
                }
            )
            epl_teams.append(team)

        # ── La Liga Teams ──────────────────────────────────────
        self.stdout.write('Creating La Liga teams...')
        esp = countries['ESP']
        liga_teams = []
        for name, short, pc, sc, stadium, cap, founded in LA_LIGA_TEAMS:
            team, _ = Team.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    'name': name, 'short_name': short, 'country': esp,
                    'primary_color': pc, 'secondary_color': sc,
                    'stadium': stadium, 'stadium_capacity': cap, 'founded': founded,
                }
            )
            liga_teams.append(team)

        all_teams = epl_teams + liga_teams

        # ── Seasons ────────────────────────────────────────────
        self.stdout.write('Creating seasons...')
        epl_season, _ = Season.objects.get_or_create(
            competition=competitions['PL'], name='2024/25',
            defaults={'start_date': date(2024, 8, 10), 'end_date': date(2025, 5, 25), 'is_current': True}
        )
        liga_season, _ = Season.objects.get_or_create(
            competition=competitions['LL'], name='2024/25',
            defaults={'start_date': date(2024, 8, 15), 'end_date': date(2025, 5, 25), 'is_current': True}
        )
        ucl_season, _ = Season.objects.get_or_create(
            competition=competitions['UCL'], name='2024/25',
            defaults={'start_date': date(2024, 9, 17), 'end_date': date(2025, 5, 31), 'is_current': True}
        )

        # ── Standings ──────────────────────────────────────────
        self.stdout.write('Creating standings...')
        self._create_standings(epl_season, epl_teams)
        self._create_standings(liga_season, liga_teams)

        # ── Players ────────────────────────────────────────────
        self.stdout.write('Creating players...')
        all_players = []
        country_list = list(countries.values())
        for team in all_teams:
            for i, pos in enumerate(POSITIONS):
                fn = random.choice(FIRST_NAMES)
                ln = random.choice(LAST_NAMES)
                display = f'{fn} {ln}'
                slug = slugify(f'{display}-{team.slug}-{i}')
                dob_year = random.randint(1992, 2005)
                player, _ = Player.objects.get_or_create(
                    slug=slug,
                    defaults={
                        'first_name': fn, 'last_name': ln, 'display_name': display,
                        'nationality': random.choice(country_list),
                        'current_team': team, 'position': pos,
                        'shirt_number': i + 1,
                        'date_of_birth': date(dob_year, random.randint(1, 12), random.randint(1, 28)),
                        'height': random.randint(168, 196),
                        'weight': random.randint(68, 92),
                        'preferred_foot': random.choice(['L', 'R', 'R', 'R']),
                        'market_value': round(random.uniform(1e6, 120e6), -5),
                    }
                )
                all_players.append((player, team))

        # ── Top Scorers ────────────────────────────────────────
        self.stdout.write('Creating top scorers...')
        epl_players = [(p, t) for p, t in all_players if t in epl_teams]
        scorer_sample = random.sample(epl_players, min(20, len(epl_players)))
        for rank, (player, team) in enumerate(scorer_sample, start=1):
            goals = max(1, 27 - rank + random.randint(-2, 3))
            TopScorer.objects.get_or_create(
                season=epl_season, player=player,
                defaults={
                    'team': team, 'goals': goals,
                    'assists': random.randint(0, 12),
                    'appearances': random.randint(20, 34),
                    'penalties': random.randint(0, 4),
                    'rank': rank,
                }
            )

        # ── Completed Matches ──────────────────────────────────
        self.stdout.write('Creating completed matches...')
        now = timezone.now()
        for i in range(25):
            home, away = random.sample(epl_teams, 2)
            hs = random.randint(0, 4)
            as_ = random.randint(0, 3)
            kickoff = now - timedelta(days=random.randint(1, 21), hours=random.randint(0, 6))
            match = Match.objects.create(
                season=epl_season, home_team=home, away_team=away,
                kickoff=kickoff, status='ft', period='fin',
                home_score=hs, away_score=as_,
                home_ht_score=random.randint(0, max(hs, 0)),
                away_ht_score=random.randint(0, max(as_, 0)),
                matchday=random.randint(1, 34),
                referee=random.choice(REFEREES), venue=home.stadium,
                attendance=random.randint(1000, max(1001, home.stadium_capacity or 50000)),
            )
            self._create_stats(match)
            self._create_goal_events(match, hs, as_, all_players, home, away)

        # ── La Liga Completed Matches ──────────────────────────
        for i in range(10):
            home, away = random.sample(liga_teams, 2)
            hs = random.randint(0, 4)
            as_ = random.randint(0, 3)
            kickoff = now - timedelta(days=random.randint(1, 14), hours=random.randint(0, 6))
            match = Match.objects.create(
                season=liga_season, home_team=home, away_team=away,
                kickoff=kickoff, status='ft', period='fin',
                home_score=hs, away_score=as_,
                home_ht_score=random.randint(0, max(hs, 0)),
                away_ht_score=random.randint(0, max(as_, 0)),
                matchday=random.randint(1, 34),
                venue=home.stadium,
                attendance=random.randint(1000, max(1001, home.stadium_capacity or 60000)),
            )
            self._create_stats(match)

        # ── Upcoming Fixtures ──────────────────────────────────
        self.stdout.write('Creating upcoming fixtures...')
        for i in range(12):
            home, away = random.sample(epl_teams, 2)
            kickoff = now + timedelta(days=random.randint(1, 14), hours=random.randint(12, 21))
            Match.objects.create(
                season=epl_season, home_team=home, away_team=away,
                kickoff=kickoff, status='scheduled', period='pre',
                matchday=random.randint(28, 38),
                venue=home.stadium,
            )
        for i in range(5):
            home, away = random.sample(liga_teams, 2)
            kickoff = now + timedelta(days=random.randint(1, 10), hours=random.randint(13, 21))
            Match.objects.create(
                season=liga_season, home_team=home, away_team=away,
                kickoff=kickoff, status='scheduled', period='pre',
                matchday=random.randint(28, 38), venue=home.stadium,
            )

        # ── Live Matches ───────────────────────────────────────
        self.stdout.write(f'Creating {options["live"]} live matches...')
        for i in range(options['live']):
            home, away = random.sample(epl_teams, 2)
            minute = random.randint(5, 85)
            hs = random.randint(0, 3)
            as_ = random.randint(0, 3)
            period = '1h' if minute <= 45 else '2h'
            match = Match.objects.create(
                season=epl_season, home_team=home, away_team=away,
                kickoff=now - timedelta(minutes=minute),
                status='live', period=period, minute=minute,
                home_score=hs, away_score=as_,
                home_ht_score=random.randint(0, max(hs, 0)) if minute > 45 else None,
                away_ht_score=random.randint(0, max(as_, 0)) if minute > 45 else None,
                matchday=random.randint(28, 38),
                referee=random.choice(REFEREES), venue=home.stadium,
                attendance=random.randint(1000, max(1001, home.stadium_capacity or 55000)),
            )
            stat = self._create_stats(match, live=True)
            self._create_goal_events(match, hs, as_, all_players, home, away, max_min=minute)
            # momentum timeline
            for m in range(1, minute + 1, 2):
                MatchMomentum.objects.get_or_create(
                    match=match, minute=m,
                    defaults={'home_value': random.randint(-70, 70)}
                )

        # ── Demo superuser ─────────────────────────────────────
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@goalpulse.com', 'admin123')
            self.stdout.write('  Created superuser: admin / admin123')

        # ── Summary ────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS('\n✅ Database seeded successfully!'))
        self.stdout.write(f'  Countries : {Country.objects.count()}')
        self.stdout.write(f'  Teams     : {Team.objects.count()}')
        self.stdout.write(f'  Players   : {Player.objects.count()}')
        self.stdout.write(f'  Matches   : {Match.objects.count()} '
                          f'({Match.objects.filter(status="live").count()} live, '
                          f'{Match.objects.filter(status="scheduled").count()} upcoming, '
                          f'{Match.objects.filter(status="ft").count()} finished)')
        self.stdout.write(f'  Standings : {Standing.objects.count()}')
        self.stdout.write(f'  Top scorers: {TopScorer.objects.count()}')

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _create_standings(self, season, teams):
        shuffled = list(teams)
        random.shuffle(shuffled)
        for pos, team in enumerate(shuffled, start=1):
            if Standing.objects.filter(season=season, team=team).exists():
                continue
            played = random.randint(28, 34)
            won = random.randint(int(played * 0.15), int(played * 0.85))
            lost = random.randint(0, played - won)
            drawn = played - won - lost
            gf = won * random.randint(1, 3) + drawn
            ga = lost * random.randint(1, 2) + drawn
            form = ''.join(random.choices(['W', 'D', 'L'], weights=[5, 2, 3], k=5))
            Standing.objects.create(
                season=season, team=team, position=pos,
                played=played, won=won, drawn=drawn, lost=lost,
                goals_for=gf, goals_against=ga,
                goal_difference=gf - ga, points=won * 3 + drawn, form=form,
            )

    def _create_stats(self, match, live=False):
        home_poss = round(random.uniform(35, 65), 1)
        home_mom = random.randint(30, 70)
        stat, _ = MatchStatistic.objects.get_or_create(
            match=match,
            defaults={
                'home_possession': home_poss,
                'away_possession': round(100 - home_poss, 1),
                'home_shots': random.randint(4, 20),
                'away_shots': random.randint(4, 18),
                'home_shots_on_target': random.randint(2, 10),
                'away_shots_on_target': random.randint(1, 8),
                'home_corners': random.randint(1, 12),
                'away_corners': random.randint(1, 10),
                'home_fouls': random.randint(4, 18),
                'away_fouls': random.randint(4, 16),
                'home_yellow_cards': random.randint(0, 4),
                'away_yellow_cards': random.randint(0, 4),
                'home_red_cards': random.randint(0, 1),
                'away_red_cards': random.randint(0, 1),
                'home_offsides': random.randint(0, 6),
                'away_offsides': random.randint(0, 6),
                'home_xg': round(random.uniform(0.4, 3.5), 2),
                'away_xg': round(random.uniform(0.3, 3.0), 2),
                'home_passes': random.randint(300, 700),
                'away_passes': random.randint(250, 600),
                'home_pass_accuracy': round(random.uniform(75, 92), 1),
                'away_pass_accuracy': round(random.uniform(72, 90), 1),
                'home_dangerous_attacks': random.randint(20, 90),
                'away_dangerous_attacks': random.randint(15, 80),
                'home_momentum': home_mom,
                'away_momentum': 100 - home_mom,
            }
        )
        return stat

    def _create_goal_events(self, match, hs, as_, all_players, home, away, max_min=90):
        home_ps = [p for p, t in all_players if t == home]
        away_ps = [p for p, t in all_players if t == away]
        for _ in range(hs):
            MatchEvent.objects.create(
                match=match, event_type='goal',
                minute=random.randint(1, max_min),
                team=home, player=random.choice(home_ps) if home_ps else None,
            )
        for _ in range(as_):
            MatchEvent.objects.create(
                match=match, event_type='goal',
                minute=random.randint(1, max_min),
                team=away, player=random.choice(away_ps) if away_ps else None,
            )
        # occasional yellow cards
        for _ in range(random.randint(0, 3)):
            team = random.choice([home, away])
            ps = home_ps if team == home else away_ps
            MatchEvent.objects.create(
                match=match, event_type='yellow_card',
                minute=random.randint(10, max_min),
                team=team, player=random.choice(ps) if ps else None,
            )
