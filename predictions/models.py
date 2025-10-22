from django.db import models
from django.contrib.auth.models import User

class Prediction(models.Model):
    user = models.ForeignKey(User, related_name='predictions', on_delete=models.CASCADE)
    match = models.ForeignKey('tournaments.Match', related_name='predictions', on_delete=models.CASCADE)
    predicted_winner = models.ForeignKey('teams.Team', related_name='predictions_on', on_delete=models.CASCADE)    
    points_awarded = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'match')

    def __str__(self):
        return f"{self.user.username}'s prediction for {self.match}"