from django.db import models
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

User = get_user_model()


# Modèle de base pour Media
class Media(models.Model):
    MEDIA_TYPES = [
        ('book', 'Book'),
        ('dvd', 'DVD'),
        ('cd', 'CD'),
        ('board_game', 'Board Game'),
    ]

    name = models.CharField(max_length=200)
    available = models.BooleanField(default=True)
    media_type = models.CharField(max_length=50, choices=MEDIA_TYPES)
    borrows = GenericRelation('Borrow', related_query_name='media')

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )

    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = models.Manager()

    def __str__(self):
        return f"{self.name} ({self.get_media_type_display()})"

    def get_media_type_display(self):
        # Correction de la méthode get_media_type_display
        return dict(self.MEDIA_TYPES).get(self.media_type, self.media_type)


# Modèle Livre (hérite de Media)
class Book(Media):
    author = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        if not self.media_type:
            self.media_type = 'book'
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(Book)
        super().save(*args, **kwargs)


# Modèle DVD (hérite de Media)
class DVD(Media):
    producer = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        if not self.media_type:
            self.media_type = 'dvd'
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(Book)
        super().save(*args, **kwargs)


# Modèle CD (hérite de Media)
class CD(Media):
    artist = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        if not self.media_type:
            self.media_type = 'cd'
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(Book)
        super().save(*args, **kwargs)


# Modèle Jeu de Plateau (hérite de Media)
class BoardGame(Media):
    creators = models.CharField(max_length=100)
    is_visible = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    game_type = models.CharField(max_length=100, blank=True, null=True)  # game_type est maintenant défini correctement

    def __str__(self):
        return self.name

    def toggle_availability(self):
        with transaction.atomic():
            # Assure qu'il n'y a pas d'emprunts actifs
            if not Borrow.objects.filter(media=self, is_returned=False).exists():
                self.is_available = not self.is_available
                self.save(update_fields=['is_available'])

    @staticmethod
    def can_borrow():
        return False  # Les jeux de plateau ne peuvent pas être empruntés

    def save(self, *args, **kwargs):
        if not self.media_type:
            self.media_type = 'board_game'
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(BoardGame)
        super().save(*args, **kwargs)


pass


class Borrow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    media = models.ForeignKey(Media, on_delete=models.CASCADE)
    borrow_date = models.DateTimeField(default=timezone.now)
    return_date = models.DateTimeField(null=True, blank=True)
    is_returned = models.BooleanField(default=False)
    due_date = models.DateTimeField()
    is_late = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_returned']),
        ]

    def get_due_date(self):
        return self.borrow_date + timedelta(days=7)

    def save(self, *args, **kwargs):
        if not self.due_date:
            self.due_date = self.borrow_date + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} emprunté {self.media.name}"

    @staticmethod
    def can_borrow(user):
        # Un utilisateur peut emprunter s'il n'a pas de retard et s'il n'a pas déjà 3 emprunts en cours
        if Borrow.objects.filter(user=user, is_returned=False).count() >= 3:
            return False
        if Borrow.objects.filter(user=user, is_late=True).exists():
            return False
        return True
