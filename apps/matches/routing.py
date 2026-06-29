from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/matches/live/$',       consumers.LiveScoreConsumer.as_asgi()),
    re_path(r'ws/matches/(?P<pk>\d+)/$', consumers.MatchDetailConsumer.as_asgi()),
]