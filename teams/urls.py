from django.urls import path
from teams.views import *

app_name = 'teams'

urlpatterns = [
    path('', show_teams, name='show_teams'),
    path('create/', create_teams, name='create_teams'),
    path('join/', join_teams, name='join_teams'),
    path('<int:team_id>/', team_details, name='team_details'),
    path('<int:team_id>/edit/', edit_team, name='edit_team'),
    path('<int:team_id>/delete/', delete_team, name='delete_team'),
    path('<int:team_id>/leave/', leave_team, name='leave_team'),
    path('<int:team_id>/members/', manage_team_members, name='manage_team_members'),
    path('<int:team_id>/tournaments/', manage_team_tournaments, name='manage_team_tournaments'),
]