from django.db import models
from django.contrib.auth.models import User

class Team(models.Model):
    name = models.CharField(max_length=255, unique=True)
    logo = models.URLField(blank=True, null=True)
    captain = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='captained_teams')
    members = models.ManyToManyField(User, related_name='teams', blank=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.members.add(self.captain)