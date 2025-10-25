from django.contrib import admin
from .models import Tournament, Match

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'organizer', 'start_date', 'end_date', 'registration_open', 'winner')
    list_filter = ('start_date', 'end_date', 'organizer', 'registration_open') 
    search_fields = ('name', 'description', 'organizer__username')
    date_hierarchy = 'start_date'
    filter_horizontal = ('participants',)

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tournament', 'match_date', 'home_score', 'away_score')
    list_filter = ('tournament', 'match_date', 'home_team', 'away_team')
    search_fields = ('tournament__name', 'home_team__name', 'away_team__name')
    date_hierarchy = 'match_date'