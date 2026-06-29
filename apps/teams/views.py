from django.views.generic import DetailView, ListView
from django.db.models import Q
from .models import Team


class TeamListView(ListView):
    model = Team
    template_name = 'teams/list.html'
    context_object_name = 'teams'
    paginate_by = 30
    queryset = Team.objects.select_related('country').order_by('name')

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query'] = self.request.GET.get('q', '')
        return ctx


class TeamDetailView(DetailView):
    model = Team
    template_name = 'teams/detail.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.matches.models import Match
        from django.utils import timezone
        ctx['recent_matches'] = Match.objects.filter(
            Q(home_team=self.object) | Q(away_team=self.object),
            status='ft'
        ).select_related('home_team', 'away_team', 'season__competition').order_by('-kickoff')[:6]
        ctx['upcoming_matches'] = Match.objects.filter(
            Q(home_team=self.object) | Q(away_team=self.object),
            status='scheduled'
        ).select_related('home_team', 'away_team', 'season__competition').order_by('kickoff')[:5]
        ctx['players'] = self.object.players.filter(is_active=True).order_by('position', 'shirt_number')
        return ctx
