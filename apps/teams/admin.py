from django.contrib import admin
from .models import Team, Country


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'country', 'stadium', 'is_national_team']
    list_filter = ['country', 'is_national_team']
    search_fields = ['name', 'stadium', 'city']
    prepopulated_fields = {'slug': ('name',)}
