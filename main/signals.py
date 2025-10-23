from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created:
        if instance.is_superuser:
            Profile.objects.get_or_create(
                user=instance, defaults={'role': 'ADMIN'})
        else:
            Profile.objects.get_or_create(
                user=instance, defaults={'role': 'PEMAIN'})
