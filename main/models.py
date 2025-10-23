from django.db import models
from django.contrib.auth.models import User
import os
from django.templatetags.static import static


class Profile(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('PENYELENGGARA', 'Penyelenggara'),
        ('PEMAIN', 'Pemain'),
    )

    REGISTRATION_ROLE_CHOICES = (
        ('PENYELENGGARA', 'Penyelenggara'),
        ('PEMAIN', 'Pemain'),
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default='PEMAIN')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.URLField(max_length=500, blank=True, null=True)

    @property
    def profile_picture_url_or_default(self):
        if self.profile_picture:
            return self.profile_picture
        else:
            return static('images/default_avatar.png')

    def __str__(self):
        return f'{self.user.username} Profile'
