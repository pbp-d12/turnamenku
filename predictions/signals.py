from django.db.models.signals import post_save
from django.dispatch import receiver
from tournaments.models import Match
from .models import Prediction

@receiver(post_save, sender=Match)
def update_predictions_after_match(sender, instance, **kwargs):
    # Kalau skor belum diisi, jangan update
    if instance.home_score is None or instance.away_score is None:
        return

    # Tentukan pemenang
    if instance.home_score > instance.away_score:
        winner = instance.home_team
    elif instance.away_score > instance.home_score:
        winner = instance.away_team
    else:
        winner = None  

    # Update poin pada setiap prediksi
    predictions = Prediction.objects.filter(match=instance)
    for pred in predictions:
        # Kalau draw
        if winner is None:
            pred.points_awarded = 0
        # Kalau prediksi benar
        elif pred.predicted_winner == winner:
            pred.points_awarded = 10
        # Kalau prediksi salah
        else:
            pred.points_awarded = -10

        pred.save()
