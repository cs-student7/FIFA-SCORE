from django.db import models
from django.utils.text import slugify
from apps.teams.models import Country, Team


class Competition(models.Model):
    COMP_TYPE_CHOICES = [
        ('league', 'League'),
        ('cup', 'Cup'),
        ('international', 'International'),
        ('friendly', 'Friendly'),
        ('playoff', 'Playoff'),
    ]
    name = models.CharField(max_length=150)
    short_name = models.CharField(max_length=20, blank=True)
    slug = models.SlugField(unique=True, max_length=160)
    logo = models.ImageField(upload_to='competitions/', null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    comp_type = models.CharField(max_length=20, choices=COMP_TYPE_CHOICES, default='league')
    tier = models.PositiveSmallIntegerField(default=1, help_text='1=top tier')
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tier', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def logo_url(self):
        if self.logo:
            return self.logo.url
        return '/static/images/default-league.svg'


class Season(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='seasons')
    name = models.CharField(max_length=20)  # e.g. "2024/25"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('competition', 'name')
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.competition.name} {self.name}'


class Standing(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='standings')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='standings')
    position = models.PositiveSmallIntegerField()
    played = models.PositiveSmallIntegerField(default=0)
    won = models.PositiveSmallIntegerField(default=0)
    drawn = models.PositiveSmallIntegerField(default=0)
    lost = models.PositiveSmallIntegerField(default=0)
    goals_for = models.PositiveSmallIntegerField(default=0)
    goals_against = models.PositiveSmallIntegerField(default=0)
    goal_difference = models.SmallIntegerField(default=0)
    points = models.PositiveSmallIntegerField(default=0)
    form = models.CharField(max_length=10, blank=True, help_text='Last 5: W/D/L')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('season', 'team')
        ordering = ['position']

    def __str__(self):
        return f'{self.position}. {self.team.name} - {self.points}pts'

    def save(self, *args, **kwargs):
        self.goal_difference = self.goals_for - self.goals_against
        super().save(*args, **kwargs)

    @property
    def form_list(self):
        return list(self.form) if self.form else []
