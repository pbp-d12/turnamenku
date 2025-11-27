from django.urls import path
from . import views

app_name = 'predictions'

urlpatterns = [
    path('', views.predictions_index, name='predictions_index'),
    path('submit/', views.submit_prediction, name='submit_prediction'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('add-match/', views.add_match, name='add_match'),
    path('evaluate/<int:match_id>/', views.evaluate_predictions, name='evaluate_predictions'),
    path('get_match_scores/<int:match_id>/', views.get_match_scores, name='get_match_scores'),
    path('edit_match_score/', views.edit_match_score, name='edit_match_score'),
    path('delete_prediction/', views.delete_prediction, name='delete_prediction'),
    path('get-ongoing-matches/', views.get_ongoing_matches, name='get_ongoing_matches'),
    path('get-finished-matches/', views.get_finished_matches, name='get_finished_matches'),
    path('api/matches/', views.get_matches_json, name='get_matches_json'),
    path('api/leaderboard/', views.get_leaderboard_json, name='get_leaderboard_json'),
    path('api/submit/', views.submit_prediction_flutter, name='submit_prediction_flutter'),
    path('api/get-form-data/', views.get_form_data, name='get_form_data'),
    path('api/create-match/', views.create_match_flutter, name='create_match_flutter'),
]