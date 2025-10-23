from django.contrib import admin
from .models import Tournament, Match

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'organizer', 'start_date', 'end_date') # Fields to show in the list view
    list_filter = ('start_date', 'end_date', 'organizer') # Fields to filter by
    search_fields = ('name', 'description', 'organizer__username') # Fields to search by
    date_hierarchy = 'start_date' # Adds date drill-down navigation

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tournament', 'match_date', 'home_score', 'away_score') # Use the model's __str__ method
    list_filter = ('tournament', 'match_date', 'home_team', 'away_team')
    search_fields = ('tournament__name', 'home_team__name', 'away_team__name')
    date_hierarchy = 'match_date'