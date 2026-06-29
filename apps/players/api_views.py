from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Player
from .serializers import PlayerSerializer


class PlayerListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PlayerSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['first_name', 'last_name', 'display_name']
    ordering_fields = ['last_name', 'position']
    ordering = ['last_name']

    def get_queryset(self):
        qs = Player.objects.select_related('current_team', 'nationality').filter(is_active=True)
        team_id = self.request.GET.get('team')
        if team_id:
            qs = qs.filter(current_team_id=team_id)
        position = self.request.GET.get('position')
        if position:
            qs = qs.filter(position=position)
        return qs


class PlayerDetailAPIView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PlayerSerializer
    queryset = Player.objects.select_related('current_team', 'nationality')
