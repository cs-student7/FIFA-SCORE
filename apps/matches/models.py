from django.db import models
from django.utils import timezone
from apps.teams.models import Team
from apps.leagues.models import Season
from apps.players.models import Player


class Match(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('ht', 'Half Time'),
        ('ft', 'Full Time'),
        ('postponed', 'Postponed'),
        ('cancelled', 'Cancelled'),
        ('abandoned', 'Abandoned'),
        ('extra_time', 'Extra Time'),
        ('penalties', 'Penalties'),
    ]
    PERIOD_CHOICES = [
        ('pre', 'Pre-Match'),
        ('1h', 'First Half'),
        ('ht', 'Half Time'),
        ('2h', 'Second Half'),
        ('et1', 'Extra Time First Half'),
        ('et2', 'Extra Time Second Half'),
        ('pen', 'Penalties'),
        ('fin', 'Finished'),
    ]

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='matches')
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    kickoff = models.DateTimeField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='scheduled', db_index=True)
    period = models.CharField(max_length=4, choices=PERIOD_CHOICES, default='pre')
    minute = models.PositiveSmallIntegerField(null=True, blank=True)
    home_score = models.PositiveSmallIntegerField(default=0)
    away_score = models.PositiveSmallIntegerField(default=0)
    home_ht_score = models.PositiveSmallIntegerField(null=True, blank=True)
    away_ht_score = models.PositiveSmallIntegerField(null=True, blank=True)
    home_et_score = models.PositiveSmallIntegerField(null=True, blank=True)
    away_et_score = models.PositiveSmallIntegerField(null=True, blank=True)
    home_pen_score = models.PositiveSmallIntegerField(null=True, blank=True)
    away_pen_score = models.PositiveSmallIntegerField(null=True, blank=True)
    matchday = models.PositiveSmallIntegerField(null=True, blank=True)
    referee = models.CharField(max_length=100, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    attendance = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-kickoff']
        indexes = [
            models.Index(fields=['status', 'kickoff']),
            models.Index(fields=['home_team', 'kickoff']),
            models.Index(fields=['away_team', 'kickoff']),
            models.Index(fields=['-kickoff']),
        ]
        ordering = ['-kickoff']

    def __str__(self):
        return f'{self.home_team} vs {self.away_team} ({self.kickoff.date()})'

    @property
    def is_live(self):
        return self.status in ('live', 'ht', 'extra_time', 'penalties')

    @property
    def score_display(self):
        if self.status == 'scheduled':
            return self.kickoff.strftime('%H:%M')
        return f'{self.home_score} - {self.away_score}'

    @property
    def competition(self):
        return self.season.competition

    @property
    def display_minute(self):
        if self.minute:
            if self.period == '1h' and self.minute > 45:
                return f"45+{self.minute - 45}'"
            if self.period == '2h' and self.minute > 90:
                return f"90+{self.minute - 90}'"
            return f"{self.minute}'"
        if self.status == 'ht':
            return 'HT'
        return ''


class MatchStatistic(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='statistics')
    home_possession = models.FloatField(default=50.0)
    away_possession = models.FloatField(default=50.0)
    home_shots = models.PositiveSmallIntegerField(default=0)
    away_shots = models.PositiveSmallIntegerField(default=0)
    home_shots_on_target = models.PositiveSmallIntegerField(default=0)
    away_shots_on_target = models.PositiveSmallIntegerField(default=0)
    home_corners = models.PositiveSmallIntegerField(default=0)
    away_corners = models.PositiveSmallIntegerField(default=0)
    home_fouls = models.PositiveSmallIntegerField(default=0)
    away_fouls = models.PositiveSmallIntegerField(default=0)
    home_yellow_cards = models.PositiveSmallIntegerField(default=0)
    away_yellow_cards = models.PositiveSmallIntegerField(default=0)
    home_red_cards = models.PositiveSmallIntegerField(default=0)
    away_red_cards = models.PositiveSmallIntegerField(default=0)
    home_offsides = models.PositiveSmallIntegerField(default=0)
    away_offsides = models.PositiveSmallIntegerField(default=0)
    home_xg = models.FloatField(default=0.0, verbose_name='Home xG')
    away_xg = models.FloatField(default=0.0, verbose_name='Away xG')
    home_passes = models.PositiveSmallIntegerField(default=0)
    away_passes = models.PositiveSmallIntegerField(default=0)
    home_pass_accuracy = models.FloatField(default=0.0)
    away_pass_accuracy = models.FloatField(default=0.0)
    home_dangerous_attacks = models.PositiveSmallIntegerField(default=0)
    away_dangerous_attacks = models.PositiveSmallIntegerField(default=0)
    home_momentum = models.PositiveSmallIntegerField(default=50, help_text='0-100 momentum score')
    away_momentum = models.PositiveSmallIntegerField(default=50)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Stats: {self.match}'


class MatchMomentum(models.Model):
    """Stores minute-by-minute momentum data for visualization"""
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='momentum_data')
    minute = models.PositiveSmallIntegerField()
    home_value = models.SmallIntegerField()  # -100 to 100 (positive = home dominance)
    event_type = models.CharField(max_length=20, blank=True)  # goal, corner, shot, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['minute']
        unique_together = ('match', 'minute')


class MatchEvent(models.Model):
    EVENT_CHOICES = [
        ('goal', 'Goal'),
        ('own_goal', 'Own Goal'),
        ('penalty', 'Penalty Goal'),
        ('penalty_miss', 'Penalty Missed'),
        ('yellow_card', 'Yellow Card'),
        ('red_card', 'Red Card'),
        ('yellow_red', 'Second Yellow'),
        ('substitution', 'Substitution'),
        ('var', 'VAR Decision'),
        ('kickoff', 'Kick Off'),
        ('half_time', 'Half Time'),
        ('full_time', 'Full Time'),
        ('injury', 'Injury'),
        ('corner', 'Corner'),
    ]
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=15, choices=EVENT_CHOICES)
    minute = models.PositiveSmallIntegerField()
    extra_time = models.PositiveSmallIntegerField(null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True)
    player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    assist_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='assists')
    player_off = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='subbed_out')
    description = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['minute', 'extra_time', 'created_at']

    def __str__(self):
        return f"{self.event_type} {self.minute}' - {self.match}"

    @property
    def minute_display(self):
        if self.extra_time:
            return f"{self.minute}+{self.extra_time}'"
        return f"{self.minute}'"


class TopScorer(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='top_scorers')
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)
    appearances = models.PositiveSmallIntegerField(default=0)
    penalties = models.PositiveSmallIntegerField(default=0)
    rank = models.PositiveSmallIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('season', 'player')
        ordering = ['rank']

    def __str__(self):
        return f'{self.player} - {self.goals} goals'
