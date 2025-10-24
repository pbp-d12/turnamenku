from django.urls import path
from teams.views import *

app_name = 'teams'

urlpatterns = [
    path('', show_main_teams, name='show_main_teams'),
    path('manage/', manage_team, name='manage_teams'),
    path('meet/', meet_team, name='meet_teams'),
    path('join/', join_team_page, name='join_teams'),
    path('create/', create_team, name='create_team'),
    path('<int:team_id>/join/', join_team, name='join_team'),
    path('<int:team_id>/edit/', edit_team, name='edit_team'),
    path('<int:team_id>/delete/', delete_team, name='delete_team'),
    path('<int:team_id>/leave/', leave_team, name='leave_team'),
    path('<int:team_id>/member/<int:member_id>/delete/', delete_member, name='delete_member'),
    path('member/<int:team_id>/<str:member_username>/delete/', delete_member, name='delete_member'),
    path('search/', search_teams, name='search_teams'),
    path('json/', show_json, name='show_json'),
]