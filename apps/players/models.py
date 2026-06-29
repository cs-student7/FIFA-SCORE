from django.db import models
from apps.teams.models import Team, Country


class Player(models.Model):
    POSITION_CHOICES = [
        ('GK', 'Goalkeeper'),
        ('CB', 'Centre-Back'),
        ('LB', 'Left-Back'),
        ('RB', 'Right-Back'),
        ('DM', 'Defensive Midfielder'),
        ('CM', 'Central Midfielder'),
        ('AM', 'Attacking Midfielder'),
        ('LW', 'Left Winger'),
        ('RW', 'Right Winger'),
        ('ST', 'Striker'),
        ('CF', 'Centre-Forward'),
    ]
    FOOT_CHOICES = [('L', 'Left'), ('R', 'Right'), ('B', 'Both')]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=150, blank=True)
    slug = models.SlugField(unique=True, max_length=200)
    photo = models.ImageField(upload_to='players/', null=True, blank=True)
    nationality = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    current_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='players')
    position = models.CharField(max_length=2, choices=POSITION_CHOICES)
    shirt_number = models.PositiveSmallIntegerField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    height = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Height in cm')
    weight = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Weight in kg')
    preferred_foot = models.CharField(max_length=1, choices=FOOT_CHOICES, blank=True)
    market_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return self.display_name or f'{self.first_name} {self.last_name}'

    @property
    def full_name(self):
        return self.display_name or f'{self.first_name} {self.last_name}'

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        from django.utils import timezone
        today = timezone.now().date()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @property
    def photo_url(self):
        if self.photo:
            return self.photo.url
        return '/static/images/default-player.svg'
