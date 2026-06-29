from django.contrib import admin
from django.utils.html import format_html
from .models import Match, MatchEvent, MatchStatistic, MatchMomentum, TopScorer


class MatchEventInline(admin.TabularInline):
    model = MatchEvent
    extra = 0
    fields = ['minute', 'extra_time', 'event_type', 'team', 'player', 'assist_player', 'description']


class MatchStatisticInline(admin.StackedInline):
    model = MatchStatistic
    can_delete = False


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'competition_name', 'kickoff', 'status', 'score_display', 'minute']
    list_filter = ['status', 'season__competition', 'kickoff']
    search_fields = ['home_team__name', 'away_team__name']
    inlines = [MatchStatisticInline, MatchEventInline]
    date_hierarchy = 'kickoff'
    list_per_page = 30

    def competition_name(self, obj):
        return obj.season.competition.name
    competition_name.short_description = 'Competition'

    def score_display(self, obj):
        if obj.status != 'scheduled':
            color = '#FF4D6D' if obj.is_live else '#aaa'
            return format_html('<b style="color:{}">{} – {}</b>', color, obj.home_score, obj.away_score)
        return '–'
    score_display.short_description = 'Score'


@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ['match', 'event_type', 'minute', 'team', 'player']
    list_filter = ['event_type']
    search_fields = ['match__home_team__name', 'match__away_team__name', 'player__last_name']


@admin.register(TopScorer)
class TopScorerAdmin(admin.ModelAdmin):
    list_display = ['rank', 'player', 'team', 'goals', 'assists', 'season']
    list_filter = ['season__competition']
