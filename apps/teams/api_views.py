from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Team
from .serializers import TeamSerializer


class TeamListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = TeamSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'short_name', 'city']
    ordering_fields = ['name']
    ordering = ['name']
    queryset = Team.objects.select_related('country').order_by('name')


class TeamDetailAPIView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = TeamSerializer
    queryset = Team.objects.select_related('country')
