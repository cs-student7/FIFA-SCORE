from django.contrib import admin
from .models import Player


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'current_team', 'position', 'nationality', 'shirt_number']
    list_filter = ['position', 'nationality', 'current_team']
    search_fields = ['first_name', 'last_name', 'display_name']
    prepopulated_fields = {'slug': ('display_name',)}
