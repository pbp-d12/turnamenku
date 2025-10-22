from django.db import models
from django.contrib.auth.models import User
import os
from django.conf import settings


def user_profile_pic_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    new_filename = f'{instance.user.username}{ext}'
    return os.path.join('profile_pics', new_filename)


class Profile(models.Model):
    ROLE_CHOICES = (
        ('PENYELENGGARA', 'Penyelenggara'),
        ('PEMAIN', 'Pemain'),
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default='PEMAIN')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to=user_profile_pic_path,
        blank=True, null=True
    )

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old_profile = Profile.objects.get(pk=self.pk)
                if old_profile.profile_picture and old_profile.profile_picture != self.profile_picture:
                    if os.path.isfile(old_profile.profile_picture.path):
                        os.remove(old_profile.profile_picture.path)
            except Profile.DoesNotExist:
                pass

        super(Profile, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.profile_picture:
            if os.path.isfile(self.profile_picture.path):
                os.remove(self.profile_picture.path)
        super(Profile, self).delete(*args, **kwargs)
