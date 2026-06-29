from django.db import models
from django.utils.text import slugify


class Country(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=3, unique=True)
    flag = models.ImageField(upload_to='flags/', null=True, blank=True)

    class Meta:
        verbose_name_plural = 'countries'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def flag_url(self):
        if self.flag:
            return self.flag.url
        return '/static/images/default-flag.svg'


class Team(models.Model):
    name = models.CharField(max_length=150)
    short_name = models.CharField(max_length=50, blank=True)
    slug = models.SlugField(unique=True, max_length=160)
    logo = models.ImageField(upload_to='teams/logos/', null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    founded = models.PositiveIntegerField(null=True, blank=True)
    stadium = models.CharField(max_length=200, blank=True)
    stadium_capacity = models.PositiveIntegerField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    primary_color = models.CharField(max_length=7, default='#ffffff')
    secondary_color = models.CharField(max_length=7, default='#000000')
    website = models.URLField(blank=True)
    is_national_team = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

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
        return '/static/images/default-team.svg'