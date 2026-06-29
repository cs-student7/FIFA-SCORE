from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Match, MatchEvent
from .serializers import MatchListSerializer


@receiver(post_save, sender=Match)
def broadcast_match_update(sender, instance, **kwargs):
    if instance.status not in ('live', 'ht', 'ft'):
        return
    channel_layer = get_channel_layer()
    data = MatchListSerializer(instance).data

    # Broadcast to live scores group
    async_to_sync(channel_layer.group_send)(
        'live_scores',
        {'type': 'score_update', 'data': data}
    )
    # Broadcast to match-specific group
    async_to_sync(channel_layer.group_send)(
        f'match_{instance.pk}',
        {'type': 'match_update', 'data': data}
    )


@receiver(post_save, sender=MatchEvent)
def broadcast_match_event(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'match_{instance.match_id}',
        {
            'type': 'match_update',
            'event': {
                'type': instance.event_type,
                'minute': instance.minute,
                'team': instance.team.short_name if instance.team else '',
                'player': instance.player.display_name if instance.player else '',
            }
        }
    )
    