from django.contrib import admin
from predictions.models import Prediction

@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'match', 'predicted_winner', 'points_awarded', 'created_at']
    list_filter = ['match__tournament', 'predicted_winner', 'points_awarded']
    search_fields = ['user__username', 'match__home_team__name', 'match__away_team__name']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
