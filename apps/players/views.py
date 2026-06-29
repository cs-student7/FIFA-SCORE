from django.views.generic import DetailView, ListView
from django.db.models import Q
from .models import Player


class PlayerListView(ListView):
    model = Player
    template_name = 'players/list.html'
    context_object_name = 'players'
    paginate_by = 30

    def get_queryset(self):
        qs = Player.objects.select_related('current_team', 'nationality').filter(is_active=True)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(display_name__icontains=q))
        pos = self.request.GET.get('position')
        if pos:
            qs = qs.filter(position=pos)
        return qs.order_by('last_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['positions'] = Player.POSITION_CHOICES
        ctx['selected_position'] = self.request.GET.get('position', '')
        return ctx


class PlayerDetailView(DetailView):
    model = Player
    template_name = 'players/detail.html'
    context_object_name = 'player'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.matches.models import MatchEvent
        ctx['goal_events'] = MatchEvent.objects.filter(
            player=self.object, event_type__in=['goal', 'penalty']
        ).select_related('match__home_team', 'match__away_team').order_by('-match__kickoff')[:10]
        return ctx
