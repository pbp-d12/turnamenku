from django.urls import path
from . import views

app_name = 'predictions'

urlpatterns = [
    path('', views.predictions_index, name='predictions_index'),
    path('submit/', views.submit_prediction, name='submit_prediction'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('evaluate/<int:match_id>/', views.evaluate_predictions, name='evaluate_predictions'),
]