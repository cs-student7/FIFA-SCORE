

from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Match
from .serializers import MatchListSerializer


@shared_task
def update_live_matches():
    """Broadcast updated live scores to all connected clients every 30s."""
    matches = Match.objects.filter(
        status__in=['live', 'ht']
    ).select_related('home_team', 'away_team', 'season__competition')

    if not matches.exists():
        return 'No live matches'

    channel_layer = get_channel_layer()
    data = MatchListSerializer(matches, many=True).data
    async_to_sync(channel_layer.group_send)(
        'live_scores',
        {'type': 'score_update', 'data': data}
    )
    return f'Broadcasted {matches.count()} live matches'