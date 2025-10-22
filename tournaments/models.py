from django.db import models
from django.contrib.auth.models import User

class Tournament(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE)
    banner = models.ImageField(upload_to='tournament_banners/', blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    participants = models.ManyToManyField('teams.Team', related_name='tournaments', blank=True)

    def __str__(self):
        return self.name

class Match(models.Model):
    tournament = models.ForeignKey(Tournament, related_name='matches', on_delete=models.CASCADE)
    home_team = models.ForeignKey('teams.Team', related_name='home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey('teams.Team', related_name='away_matches', on_delete=models.CASCADE)
    match_date = models.DateTimeField()
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} ({self.tournament.name})"