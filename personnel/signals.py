from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Member

@receiver(post_save, sender=User)
def create_member_for_user(sender, instance, created, **kwargs):
    """Créer un Member lorsqu'un User est créé."""
    if created:
        Member.objects.create(user=instance)

@receiver(post_save, sender=User)
def create_member_for_user(sender, instance, created, **kwargs):
    if created:
        # Assure-toi que l'argument '_' est passé ou que la fonction est correcte.
        Member.objects.create(user=instance)

