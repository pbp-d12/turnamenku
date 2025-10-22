from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = (
        ('PENYELENGGARA', 'Penyelenggara'),
        ('PEMAIN', 'Pemain'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile') 
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PEMAIN')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} Profile'
