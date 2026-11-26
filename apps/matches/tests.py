from unittest.mock import patch
from unittest.mock import Mock
from datetime import date, timedelta

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from requests.exceptions import Timeout

from apps.core.services.football_data import FootballDataClient
from apps.matches.football_api import (
    get_fixtures_by_date,
    get_league_standings,
)

from .football_api import (
    _ap_cache_keys,
    _ap_get,
    _wc_get,
    get_fixture_full_details,
)


class FixtureCenterDataTests(SimpleTestCase):
    def tearDown(self):
        stale_key, cooldown_key, _legacy_stale_key = _ap_cache_keys(
            'fixtures', {'id': 987654}
        )
        for key in (
            'ap_fixture_full_987654',
            'ap_events_987654',
            'ap_lineups_987654',
            'ap_stats_987654',
            'ap_player_stats_987654',
            'public_match_notifications',
            'stale_get/games',
            'wc_error_cooldown_get/games',
            'ap_fixtures_date_2099-12-31',
            'pl_matches_v4',
            stale_key,
            cooldown_key,
        ):
            cache.delete(key)

    @override_settings(API_FOOTBALL_KEY='test-api-key')
    @patch('apps.matches.football_api._ap_get')
    def test_fixture_center_combines_live_match_data(self, api_get):
        fixture = {
            'fixture': {'status': {'short': '1H'}},
            'teams': {'home': {'id': 1}, 'away': {'id': 2}},
            'goals': {'home': 1, 'away': 0},
        }
        data_by_endpoint = {
            'fixtures': [fixture],
            'fixtures/events': [{'type': 'Goal', 'time': {'elapsed': 12}}],
            'fixtures/lineups': [{'team': {'id': 1}, 'startXI': []}],
            'fixtures/statistics': [{'team': {'id': 1}, 'statistics': []}],
            'fixtures/players': [{'team': {'id': 1}, 'players': []}],
        }
        api_get.side_effect = lambda endpoint, params: data_by_endpoint[endpoint]

        result = get_fixture_full_details(987654)

        self.assertEqual(result['fixture'], fixture['fixture'])
        self.assertEqual(result['events'][0]['time']['elapsed'], 12)
        self.assertEqual(result['lineups'][0]['team']['id'], 1)
        self.assertEqual(result['statistics'][0]['team']['id'], 1)
        self.assertEqual(result['players'][0]['team']['id'], 1)

    @override_settings(API_FOOTBALL_KEY='test-api-key')
    @patch('apps.matches.football_api.cache.set')
    @patch('apps.matches.football_api._ap_get')
    def test_completed_fixture_caches_complete_details_for_one_day(
        self, api_get, cache_set
    ):
        data_by_endpoint = {
            'fixtures': [{'fixture': {'status': {'short': 'FT'}}}],
            'fixtures/events': [{'type': 'Goal'}],
            'fixtures/lineups': [{'team': {'id': 1}}],
            'fixtures/statistics': [{'team': {'id': 1}}],
            'fixtures/players': [{'team': {'id': 1}}],
        }
        api_get.side_effect = lambda endpoint, params: data_by_endpoint[endpoint]

        result = get_fixture_full_details(987654)

        self.assertTrue(
            all(result[key] for key in ('events', 'lineups', 'statistics', 'players'))
        )
        cache_set.assert_any_call('ap_fixture_full_987654', result, 86400)

    @override_settings(API_FOOTBALL_KEY='api-football-key', API_TOKEN='football-data-token')
    @patch('apps.matches.football_api.requests.get')
    def test_api_limit_uses_stale_data_and_throttles_retries(self, get):
        params = {'id': 987654}
        stale = [{'fixture': {'id': 987654}}]
        stale_key, cooldown_key, _ = _ap_cache_keys('fixtures', params)
        cache.delete(cooldown_key)
        cache.set(stale_key, stale, 60)
        response = Mock()
        response.json.return_value = {
            'errors': {'requests': 'You have reached the request limit for the day.'}
        }
        get.return_value = response

        self.assertEqual(_ap_get('fixtures', params), stale)
        self.assertEqual(_ap_get('fixtures', params), stale)
        get.assert_called_once()

    @patch('apps.matches.football_api.requests.get')
    def test_world_cup_timeout_uses_stale_data_and_throttles_retries(self, get):
        stale = {'games': [{'home_team_name_en': 'Home FC'}]}
        cache.set('stale_get/games', stale, 60)
        get.side_effect = Timeout('provider unavailable')

        self.assertEqual(_wc_get('get/games'), stale)
        self.assertEqual(_wc_get('get/games'), stale)
        get.assert_called_once()

    @override_settings(
        API_TOKEN='football-data-token',
        WC_API_TOKEN='world-cup-token',
    )
    @patch('apps.matches.football_api.requests.get')
    def test_world_cup_request_uses_api_token(self, get):
        response = Mock()
        response.json.return_value = {'games': []}
        get.return_value = response

        self.assertEqual(_wc_get('get/api-token-test'), {'games': []})

        get.assert_called_once_with(
            'http://worldcup26.ir:3050/get/api-token-test',
            headers={'Authorization': 'Bearer world-cup-token'},
            timeout=3,
        )

    @override_settings(API_FOOTBALL_KEY='api-football-key', API_TOKEN='football-data-token')
    @patch('apps.matches.football_api.requests.get')
    def test_api_football_does_not_use_football_data_token(self, get):
        success_response = Mock(status_code=200)
        success_response.json.return_value = {'response': [{'id': 112233}]}
        get.return_value = success_response

        result = _ap_get('fixtures', {'date': '2099-12-30'})

        self.assertEqual(result, [{'id': 112233}])
        get.assert_called_once()
        self.assertEqual(
            get.call_args.kwargs['headers']['x-apisports-key'],
            'api-football-key',
        )

    @override_settings(API_TOKEN='football-data-token')
    @patch('apps.core.services.football_data.cache.set')
    @patch('apps.core.services.football_data.cache.get', return_value=None)
    @patch('apps.core.services.football_data.requests.get')
    def test_football_data_matches_use_v4_auth_response_and_cache(
        self, get, cache_get, cache_set
    ):
        response = Mock()
        response.json.return_value = {'matches': [{'id': 112233}]}
        get.return_value = response

        matches = FootballDataClient().get_matches('PL')

        self.assertEqual(matches, [{'id': 112233}])
        get.assert_called_once_with(
            'https://api.football-data.org/v4/competitions/PL/matches',
            headers={'X-Auth-Token': 'football-data-token'},
            params=None,
            timeout=10,
        )
        cache_set.assert_called_once()
        cache_key = cache_set.call_args.args[0]
        self.assertTrue(cache_key.startswith('fd_v4_'))
        cache_get.assert_called_once_with(cache_key)
        self.assertEqual(
            cache_set.call_args.args[1:],
            ({'matches': matches}, 120),
        )

    @override_settings(API_FOOTBALL_KEY='')
    @patch('apps.matches.football_api.FootballDataClient.get_matches_by_date')
    def test_fixture_list_uses_football_data_v4_and_template_shape(self, get_matches):
        get_matches.return_value = [{
            'id': 112233,
            'competition': {
                'code': 'PL',
                'name': 'Premier League',
                'emblem': 'https://example.test/pl.png',
            },
            'utcDate': '2026-11-26T19:00:00Z',
            'status': 'SCHEDULED',
            'homeTeam': {'id': 1, 'name': 'Home FC', 'crest': ''},
            'awayTeam': {'id': 2, 'name': 'Away FC', 'crest': ''},
            'score': {'fullTime': {'home': None, 'away': None}},
        }]

        fixtures = get_fixtures_by_date('2026-11-26', league_id=39)

        self.assertEqual(fixtures[0]['fixture']['id'], 112233)
        self.assertEqual(fixtures[0]['fixture']['status']['short'], 'NS')
        self.assertEqual(fixtures[0]['league']['id'], 39)
        self.assertEqual(fixtures[0]['teams']['home']['name'], 'Home FC')
        get_matches.assert_called_once_with(
            '2026-11-26', '2026-11-26', ['PL'], status=None
        )

    @patch('apps.matches.views.get_fd_matches_by_date')
    def test_fixture_page_renders_matches_returned_by_provider(self, fixtures):
        fixtures.return_value = [{
            'id': 112233,
            'utcDate': '2026-11-26T19:00:00Z',
            'status': 'SCHEDULED',
            'competition': {
                'code': 'PL',
                'name': 'Premier League',
                'emblem': '',
            },
            'homeTeam': {'id': 1, 'name': 'Home FC', 'crest': ''},
            'awayTeam': {'id': 2, 'name': 'Away FC', 'crest': ''},
            'score': {'fullTime': {'home': None, 'away': None}},
        }]

        response = self.client.get('/matches/?date=2026-11-26&league=39')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Home FC')
        self.assertContains(response, 'Away FC')
        self.assertContains(response, 'Premier League')

    @patch('apps.matches.views.get_fd_matches_by_date')
    def test_empty_fixture_day_shows_upcoming_matches(
        self, fixtures_by_date
    ):
        start_day = date.today()
        upcoming_match = {
            'id': 112234,
            'utcDate': (start_day + timedelta(days=2)).isoformat() + 'T19:00:00Z',
            'status': 'SCHEDULED',
            'competition': {
                'code': 'PL',
                'name': 'Premier League',
                'emblem': '',
            },
            'homeTeam': {'id': 1, 'name': 'Next Home FC', 'crest': ''},
            'awayTeam': {'id': 2, 'name': 'Next Away FC', 'crest': ''},
            'score': {'fullTime': {'home': None, 'away': None}},
        }
        fixtures_by_date.side_effect = [[], [upcoming_match]]

        response = self.client.get(
            f'/matches/?date={start_day.isoformat()}&league=39'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No matches are scheduled')
        self.assertContains(response, 'Next Home FC')
        self.assertContains(response, 'Next Away FC')
        self.assertEqual(fixtures_by_date.call_count, 2)

    @patch('apps.core.views.Competition.objects.filter', return_value=[])
    @patch('apps.core.views.get_wc_groups', return_value=[])
    @patch('apps.core.views.get_wc_results', return_value=[])
    @patch('apps.core.views.get_wc_upcoming', return_value=[])
    @patch('apps.core.views.get_wc_live_matches', return_value=[])
    @patch('apps.core.views.get_weekly_matches')
    def test_home_page_renders_raw_v4_match_fields(
        self, weekly_matches, _wc_live, _wc_upcoming, _wc_results, _wc_groups,
        _competitions,
    ):
        weekly_matches.return_value = [{
            'id': 112235,
            'utcDate': '2026-11-26T19:00:00Z',
            'status': 'SCHEDULED',
            'competition': {
                'name': 'Premier League',
                'emblem': '',
                'code': 'PL',
            },
            'homeTeam': {'name': 'Home FC', 'crest': ''},
            'awayTeam': {'name': 'Away FC', 'crest': ''},
            'score': {'fullTime': {'home': None, 'away': None}},
        }]

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Matches This Week')
        self.assertContains(response, 'Premier League')
        self.assertContains(response, 'Home FC')
        self.assertContains(response, 'Away FC')

    @patch('apps.leagues.views.get_standings')
    def test_standings_page_renders_v4_fields(self, standings):
        standings.return_value = [{
            'position': 1,
            'team': {'name': 'Home FC', 'crest': ''},
            'playedGames': 10,
            'won': 8,
            'draw': 1,
            'lost': 1,
            'goalsFor': 24,
            'goalsAgainst': 8,
            'goalDifference': 16,
            'points': 25,
            'form': 'W,W,D,W,W',
        }]

        response = self.client.get('/leagues/?league=39')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Home FC')
        self.assertContains(response, '25')

    @patch('apps.players.views.get_fd_top_scorers')
    def test_scorers_page_renders_v4_fields(self, scorers):
        scorers.return_value = [{
            'player': {'name': 'Example Scorer', 'nationality': 'England'},
            'team': {'name': 'Home FC', 'crest': ''},
            'playedMatches': 10,
            'goals': 8,
            'assists': 2,
        }]

        response = self.client.get('/players/?league=39')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Example Scorer')
        self.assertContains(response, 'Home FC')
        self.assertContains(response, '8')

    @override_settings(API_FOOTBALL_KEY='')
    @patch('apps.matches.football_api.FootballDataClient.get_standings')
    def test_standings_use_football_data_v4_table_shape(self, get_standings):
        cache.delete('football_data_standings_39_2026')
        get_standings.return_value = {
            'standings': [{
                'type': 'TOTAL',
                'table': [{
                    'position': 1,
                    'team': {'id': 1, 'name': 'Home FC', 'crest': ''},
                    'playedGames': 10,
                    'won': 8,
                    'draw': 1,
                    'lost': 1,
                    'goalsFor': 24,
                    'goalsAgainst': 8,
                    'goalDifference': 16,
                    'points': 25,
                    'form': 'W,W,D,W,W',
                }],
            }],
        }

        rows = get_league_standings(league_id=39)

        self.assertEqual(rows[0]['rank'], 1)
        self.assertEqual(rows[0]['all']['played'], 10)
        self.assertEqual(rows[0]['all']['goals']['for'], 24)
        self.assertEqual(rows[0]['points'], 25)
        get_standings.assert_called_once_with('PL')

    @patch('apps.matches.api_views.get_match_events')
    @patch('apps.matches.api_views.get_today_matches', return_value=[])
    @patch('apps.matches.api_views.get_live_matches')
    def test_match_notifications_are_public_and_match_only(
        self, live_matches, _today_matches, match_events
    ):
        live_matches.return_value = [{
            'id': 987654,
            'league_name': 'Example League',
            'home_team': {'name': 'Home FC'},
            'away_team': {'name': 'Away FC'},
        }]
        match_events.return_value = [{
            'time': {'elapsed': 12, 'extra': None},
            'team': {'name': 'Home FC'},
            'player': {'name': 'Player One'},
            'assist': {'name': 'Player Two'},
            'type': 'Goal',
            'detail': 'Normal Goal',
        }]
        cache.delete('public_match_notifications')

        response = self.client.get('/api/v1/matches/notifications/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['fixture_id'], 987654)
        self.assertEqual(response.data[0]['player'], 'Player One')
