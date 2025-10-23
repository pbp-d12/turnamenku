from django.db.models.signals import post_save, pre_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile, user_profile_pic_path
import os
from django.conf import settings


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created:
        if instance.is_superuser:
            Profile.objects.get_or_create(
                user=instance, defaults={'role': 'ADMIN'})
        else:
            Profile.objects.get_or_create(
                user=instance, defaults={'role': 'PEMAIN'})


@receiver(pre_save, sender=User)
def store_old_username(sender, instance, **kwargs):
    """Simpan username lama sebelum User di-save."""
    if instance.pk:
        try:
            instance._old_username = User.objects.get(pk=instance.pk).username
        except User.DoesNotExist:
            instance._old_username = None
    else:
        instance._old_username = None


@receiver(post_save, sender=User)
def rename_profile_picture_on_username_change(sender, instance, created, **kwargs):
    """Ganti nama file foto profil SETELAH User di-save jika username berubah."""
    if not created and hasattr(instance, '_old_username') and instance._old_username != instance.username:
        old_username = instance._old_username
        new_username = instance.username

        try:
            profile = instance.profile
            if profile.profile_picture:
                old_path_relative = profile.profile_picture.name

                filename_only = os.path.basename(old_path_relative)
                name_part, ext = os.path.splitext(filename_only)

                if name_part == old_username:
                    new_filename = f"{new_username}{ext}"
                    new_path_relative = os.path.join(
                        'profile_pics', new_filename)

                    old_path_full = os.path.join(
                        settings.MEDIA_ROOT, old_path_relative)
                    new_path_full = os.path.join(
                        settings.MEDIA_ROOT, new_path_relative)

                    if os.path.exists(old_path_full):
                        try:
                            os.rename(old_path_full, new_path_full)
                            profile.profile_picture.name = new_path_relative
                            profile.save(update_fields=['profile_picture'])
                            print(
                                f"Renamed profile picture from {old_path_relative} to {new_path_relative}")
                        except OSError as e:
                            print(f"Error renaming file: {e}")
                    else:
                        print(f"Old file not found: {old_path_full}")

        except Profile.DoesNotExist:
            pass

    if hasattr(instance, '_old_username'):
        del instance._old_username
