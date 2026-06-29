import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Match
from .serializers import MatchListSerializer


class LiveScoreConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('live_scores', self.channel_name)
        await self.accept()
        # Send current live matches on connect
        matches = await self.get_live_matches()
        await self.send(json.dumps({'type': 'live_scores', 'data': matches}))

    async def disconnect(self, code):
        await self.channel_layer.group_discard('live_scores', self.channel_name)

    async def score_update(self, event):
        await self.send(json.dumps(event))

    @database_sync_to_async
    def get_live_matches(self):
        matches = Match.objects.filter(
            status__in=['live', 'ht']
        ).select_related('home_team', 'away_team', 'season__competition')
        return MatchListSerializer(matches, many=True).data


class MatchDetailConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.pk = self.scope['url_route']['kwargs']['pk']
        self.group = f'match_{self.pk}'
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    async def match_update(self, event):
        await self.send(json.dumps(event))