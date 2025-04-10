from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Member

@receiver(post_save, sender=User)
def create_member_for_user(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'member'):
        Member.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_member(sender, instance, **kwargs):
    if hasattr(instance, 'member'):
        instance.member.save()
