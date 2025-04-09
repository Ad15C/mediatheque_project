from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Member

@receiver(post_save, sender=User)
def create_member_for_user(_, instance, created, **kwargs):
    if created:
        member = Member.objects.create(user=instance)
        print(f"Un membre a été créé pour {instance.username} avec l'ID {member.id}")

@receiver(post_save, sender=User)
def save_member(_, instance, **kwargs):
    # Sauvegarde le membre associé à l'utilisateur
    if hasattr(instance, 'member'):
        instance.member.save()
