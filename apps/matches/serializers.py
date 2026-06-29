from rest_framework import serializers
from .models import Match, MatchStatistic, MatchEvent, MatchMomentum, TopScorer
from apps.teams.models import Team
from apps.leagues.models import Competition, Standing


class TeamMiniSerializer(serializers.ModelSerializer):
    logo_url = serializers.ReadOnlyField()
    class Meta:
        model = Team
        fields = ['id', 'name', 'short_name', 'slug', 'logo_url', 'primary_color']


class CompetitionMiniSerializer(serializers.ModelSerializer):
    logo_url = serializers.ReadOnlyField()
    class Meta:
        model = Competition
        fields = ['id', 'name', 'short_name', 'slug', 'logo_url']


class MatchEventSerializer(serializers.ModelSerializer):
    player_name = serializers.SerializerMethodField()
    assist_name = serializers.SerializerMethodField()
    team_id = serializers.IntegerField(source='team.id', allow_null=True)
    minute_display = serializers.ReadOnlyField()

    class Meta:
        model = MatchEvent
        fields = ['id', 'event_type', 'minute', 'extra_time', 'minute_display',
                  'team_id', 'player_name', 'assist_name', 'description']

    def get_player_name(self, obj):
        return obj.player.full_name if obj.player else ''

    def get_assist_name(self, obj):
        return obj.assist_player.full_name if obj.assist_player else ''


class MatchStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchStatistic
        fields = ['home_possession', 'away_possession', 'home_shots', 'away_shots', 
                  'home_shots_on_target', 'away_shots_on_target', 'home_corners', 'away_corners',
                  'home_fouls', 'away_fouls', 'home_yellow_cards', 'away_yellow_cards',
                  'home_red_cards', 'away_red_cards', 'home_offsides', 'away_offsides',
                  'home_xg', 'away_xg', 'home_passes', 'away_passes', 'home_pass_accuracy',
                  'away_pass_accuracy', 'home_dangerous_attacks', 'away_dangerous_attacks',
                  'home_momentum', 'away_momentum']


class MatchMomentumSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchMomentum
        fields = ['minute', 'home_value', 'event_type']


class MatchListSerializer(serializers.ModelSerializer):
    home_team = TeamMiniSerializer()
    away_team = TeamMiniSerializer()
    competition = CompetitionMiniSerializer(source='season.competition')
    display_minute = serializers.ReadOnlyField()
    score_display = serializers.ReadOnlyField()

    class Meta:
        model = Match
        fields = ['id', 'home_team', 'away_team', 'competition', 'kickoff',
                  'status', 'period', 'minute', 'display_minute', 'score_display',
                  'home_score', 'away_score', 'home_ht_score', 'away_ht_score', 'matchday']


class MatchDetailSerializer(MatchListSerializer):
    events = MatchEventSerializer(many=True, allow_null=True)
    statistics = MatchStatisticSerializer(allow_null=True)
    momentum_data = MatchMomentumSerializer(many=True, allow_null=True)

    class Meta(MatchListSerializer.Meta):
        fields = MatchListSerializer.Meta.fields + [
            'events', 'statistics', 'momentum_data',
            'referee', 'venue', 'attendance',
            'home_et_score', 'away_et_score', 'home_pen_score', 'away_pen_score'
        ]


class StandingSerializer(serializers.ModelSerializer):
    team = TeamMiniSerializer()
    form_list = serializers.ReadOnlyField()

    class Meta:
        model = Standing
        fields = ['position', 'team', 'played', 'won', 'drawn', 'lost',
                  'goals_for', 'goals_against', 'goal_difference', 'points', 'form_list']


class TopScorerSerializer(serializers.ModelSerializer):
    player_name = serializers.SerializerMethodField()
    team_name = serializers.SerializerMethodField()
    team_short = serializers.SerializerMethodField()

    class Meta:
        model = TopScorer
        fields = ['rank', 'player_name', 'team_name', 'team_short',
                  'goals', 'assists', 'appearances', 'penalties']

    def get_player_name(self, obj):
        return obj.player.full_name if obj.player else ''

    def get_team_name(self, obj):
        return obj.team.name if obj.team else ''

    def get_team_short(self, obj):
        return obj.team.short_name if obj.team else ''
