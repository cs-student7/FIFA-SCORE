from django.contrib import admin
from .models import Competition, Season, Standing


class SeasonInline(admin.TabularInline):
    model = Season
    extra = 0


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'comp_type', 'tier', 'is_featured', 'is_active']
    list_filter = ['comp_type', 'tier', 'is_featured']
    search_fields = ['name']
    inlines = [SeasonInline]
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'start_date', 'end_date', 'is_current']
    list_filter = ['competition', 'is_current']


@admin.register(Standing)
class StandingAdmin(admin.ModelAdmin):
    list_display = ['position', 'team', 'season', 'played', 'won', 'drawn', 'lost', 'points']
    list_filter = ['season__competition']
