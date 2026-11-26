from unittest.mock import patch
from unittest.mock import Mock
from datetime import date, datetime, timezone

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from requests.exceptions import Timeout

from .football_api import (
    _ap_cache_keys,
    _ap_get,
    _fd5_get,
    _fd5_upcoming_or_today,
    _wc_get,
    get_fixture_full_details,
    get_fixtures_by_date,
    get_today_matches,
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
            'fd5_upcoming_or_today_2099-12-28',
            stale_key,
            cooldown_key,
        ):
            cache.delete(key)

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

    @patch('apps.matches.football_api.requests.get')
    def test_api_limit_uses_stale_data_and_throttles_retries(self, get):
        params = {'id': 987654}
        stale = [{'fixture': {'id': 987654}}]
        stale_key, _, _ = _ap_cache_keys('fixtures', params)
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

    @override_settings(API_TOKEN='api-token', WC_API_TOKEN='legacy-token')
    @patch('apps.matches.football_api.requests.get')
    def test_world_cup_request_uses_api_token(self, get):
        response = Mock()
        response.json.return_value = {'games': []}
        get.return_value = response

        self.assertEqual(_wc_get('get/api-token-test'), {'games': []})

        get.assert_called_once_with(
            'http://worldcup26.ir:3050/get/api-token-test',
            headers={'Authorization': 'Bearer api-token'},
            timeout=3,
        )

    @override_settings(FIVE_DOLLAR_API_KEY='test-key')
    @patch('apps.matches.football_api._fd5_get')
    @patch('apps.matches.football_api._ap_get', return_value=[])
    def test_date_fixtures_fall_back_to_secondary_provider(
        self, api_get, fallback_get
    ):
        fallback_get.return_value = [{
            'id': 112233,
            'date': '2099-12-31T12:00:00Z',
            'league': {'id': 39, 'name': 'Premier League'},
            'home_team': {'id': 1, 'name': 'Home FC'},
            'away_team': {'id': 2, 'name': 'Away FC'},
            'status': 'scheduled',
            'score': {'home': None, 'away': None},
        }]

        fixtures = get_fixtures_by_date('2099-12-31')

        self.assertEqual(fixtures[0]['fixture']['id'], 112233)
        self.assertEqual(fixtures[0]['teams']['home']['name'], 'Home FC')
        api_get.assert_called_once()
        start_ts = int(
            datetime.strptime('2099-12-31', '%Y-%m-%d')
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
        fallback_get.assert_called_once_with(
            'fixtures',
            {
                'start_time': start_ts,
                'end_time': start_ts + 86400,
                'include': 'events,stats',
            },
        )

    @override_settings(
        FIVE_DOLLAR_API_KEY='first-key',
        FIVE_DOLLAR_API_KEY_2='second-key',
    )
    @patch('apps.matches.football_api.cache.set')
    @patch('apps.matches.football_api.requests.get')
    def test_fd5_retries_with_second_key_after_rate_limit(
        self, get, _cache_set
    ):
        limited_response = Mock(status_code=429)
        success_response = Mock(status_code=200)
        success_response.json.return_value = {'data': [{'id': 112233}]}
        get.side_effect = [limited_response, success_response]

        result = _fd5_get('fixtures', {'date': '2099-12-30'})

        self.assertEqual(result, [{'id': 112233}])
        self.assertEqual(get.call_count, 2)
        self.assertEqual(
            get.call_args_list[0].kwargs['headers']['Authorization'],
            'Bearer first-key',
        )
        self.assertEqual(
            get.call_args_list[1].kwargs['headers']['Authorization'],
            'Bearer second-key',
        )

    @override_settings(
        FIVE_DOLLAR_API_KEY='first-key',
        FIVE_DOLLAR_API_KEY_2='second-key',
    )
    @patch('apps.matches.football_api.cache.set')
    @patch('apps.matches.football_api.requests.get')
    def test_fd5_retries_with_second_key_after_auth_error(
        self, get, _cache_set
    ):
        auth_error_response = Mock(status_code=401)
        success_response = Mock(status_code=200)
        success_response.json.return_value = {'data': [{'id': 112234}]}
        get.side_effect = [auth_error_response, success_response]

        result = _fd5_get('fixtures', {'date': '2099-12-29'})

        self.assertEqual(result, [{'id': 112234}])
        self.assertEqual(get.call_count, 2)
        self.assertEqual(
            get.call_args_list[0].kwargs['headers']['Authorization'],
            'Bearer first-key',
        )
        self.assertEqual(
            get.call_args_list[1].kwargs['headers']['Authorization'],
            'Bearer second-key',
        )

    @patch('apps.matches.football_api._fd5_get')
    @patch(
        'apps.matches.football_api._fd5_fixtures_for_date',
        return_value=[],
    )
    def test_fd5_upcoming_fallback_queries_five_leagues_and_sorts(
        self, _today_fixtures, fd5_get
    ):
        cache.delete('fd5_upcoming_or_today_2099-12-28')
        fd5_get.side_effect = lambda endpoint, params=None: (
            [{'id': league_id} for league_id in range(1, 6)]
            if endpoint == 'leagues'
            else [{
                'id': 100 + int(endpoint.split('/')[1]),
                'timestamp': 600 - int(endpoint.split('/')[1]) * 100,
                'league': {'id': int(endpoint.split('/')[1])},
                'home_team': {'name': 'Home FC'},
                'away_team': {'name': 'Away FC'},
                'status': 'scheduled',
            }]
        )

        fixtures = _fd5_upcoming_or_today('2099-12-28')

        self.assertEqual(len(fixtures), 5)
        self.assertEqual(
            [fixture['fixture']['timestamp'] for fixture in fixtures],
            [100, 200, 300, 400, 500],
        )
        fd5_get.assert_any_call(
            'leagues/1/fixtures', {'status': 'scheduled', 'per_page': 5}
        )
        fd5_get.assert_any_call(
            'leagues/5/fixtures', {'status': 'scheduled', 'per_page': 5}
        )

    @override_settings(FIVE_DOLLAR_API_KEY='', FIVE_DOLLAR_API_KEY_2='second-key')
    @patch('apps.matches.football_api._fd5_upcoming_or_today')
    @patch('apps.matches.football_api.get_fixtures_by_date', return_value=[])
    def test_today_matches_uses_upcoming_fallback_with_secondary_key(
        self, fixtures_by_date, upcoming
    ):
        upcoming.return_value = [{'fixture': {'id': 112233}}]

        result = get_today_matches()

        self.assertEqual(result, upcoming.return_value)
        upcoming.assert_called_once_with(date.today().isoformat())
        self.assertEqual(fixtures_by_date.call_count, 2)

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
