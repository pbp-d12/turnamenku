from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created:
        role_from_form = None
        if hasattr(instance, '_registration_role'):
            role_from_form = instance._registration_role
            try:
                del instance._registration_role
            except AttributeError:
                pass

        role_to_set = None

        if role_from_form:
            role_to_set = role_from_form
        elif instance.is_superuser:
            role_to_set = 'ADMIN'
        else:
            role_to_set = 'PEMAIN'

        Profile.objects.get_or_create(
            user=instance, defaults={'role': role_to_set})

        if hasattr(instance, '_registration_role'):
            try:
                del instance._registration_role
            except AttributeError:
                pass
