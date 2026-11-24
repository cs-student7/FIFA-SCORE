from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase

from .football_api import get_fixture_full_details


class FixtureCenterDataTests(SimpleTestCase):
    def tearDown(self):
        cache.clear()

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
