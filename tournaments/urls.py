from django.urls import path
from . import views 

app_name = 'tournaments'

urlpatterns = [
    path('', views.tournament_home, name='tournament_home'),
    path('json/', views.get_tournaments_json, name='get_tournaments_json'),
    path('<int:tournament_id>/', views.tournament_detail_page, name='tournament_detail_page'),
    path('json/<int:tournament_id>/', views.get_tournament_detail_json, name='get_tournament_detail_json'),
    path('create/', views.create_tournament, name='create_tournament'),
    path('edit/<int:tournament_id>/', views.edit_tournament, name='edit_tournament'),
]