from django.views.generic import DetailView, ListView
from django.utils import timezone
from .models import Match, MatchStatistic


class MatchListView(ListView):
    model = Match
    template_name = 'matches/list.html'
    context_object_name = 'matches'
    paginate_by = 30

    def get_queryset(self):
        qs = Match.objects.select_related('home_team__country', 'away_team__country', 'season__competition__country').prefetch_related('statistics')
        date_str = self.request.GET.get('date')
        if date_str:
            from datetime import datetime
            try:
                d = datetime.strptime(date_str, '%Y-%m-%d').date()
                qs = qs.filter(kickoff__date=d)
            except ValueError:
                qs = qs.filter(kickoff__date=timezone.now().date())
        else:
            qs = qs.filter(kickoff__date=timezone.now().date())
        return qs.order_by('status', 'kickoff')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['selected_date'] = self.request.GET.get('date', timezone.now().date().isoformat())
        ctx['live_count'] = self.get_queryset().filter(status__in=['live', 'ht']).count()
        return ctx


class MatchDetailView(DetailView):
    model = Match
    template_name = 'matches/detail.html'
    context_object_name = 'match'

    def get_queryset(self):
        return Match.objects.select_related(
            'home_team__country', 'away_team__country', 'season__competition__country'
        ).prefetch_related('events__player', 'events__team', 'statistics', 'momentum_data')
        
        