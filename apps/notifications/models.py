from django.db import models
from django.contrib.auth.models import User
from apps.matches.models import Match

class Notification(models.Model):
    TYPE_CHOICES = [
        ('goal', 'Goal'),
        ('match_start', 'Match Start'),
        ('match_end', 'Match End'),
        ('red_card', 'Red Card'),
        ('var', 'VAR Decision'),
        ('substitution', 'Substitution'),
        ('system', 'System'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.notification_type}: {self.title}'