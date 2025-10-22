from django.urls import path
from predictions.views import prediction_list, submit_prediction, evaluate_predictions, leaderboard_view

app_name = 'predictions'

urlpatterns = [
    path('<int:tournament_id>/', prediction_list, name='prediction_list'),
    path('submit/', submit_prediction, name='submit_prediction'),
    path('evaluate/<int:match_id>/', evaluate_predictions, name='evaluate_predictions'),
    path('leaderboard/<int:tournament_id>/', leaderboard_view, name='leaderboard'),
]