from mediatheque.models import Media
from django.db import models, transaction
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

# Obtenez l'utilisateur personnalisé (si vous avez un modèle personnalisé)
User = get_user_model()


# Modèle de base pour les emprunts
class StaffBorrow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='staff_borrow_set')  # Changement de related_name
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
        if StaffBorrow.objects.filter(user=user, is_returned=False).count() >= 3:
            return False
        if StaffBorrow.objects.filter(user=user, is_late=True).exists():
            return False
        return True


# Modèle Media spécifique à l'application `staff`
class MediaStaff(models.Model):
    MEDIA_TYPES = [
        ('book', 'Book'),
        ('dvd', 'DVD'),
        ('cd', 'CD'),
        ('board_game', 'Board Game'),
    ]

    name = models.CharField(max_length=200)
    available = models.BooleanField(default=True)
    media_type = models.CharField(max_length=50, choices=MEDIA_TYPES)
    borrows = GenericRelation(StaffBorrow, related_query_name='staff_media')
    can_borrow = models.BooleanField(default=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,
                                     related_name='staff_media_set')  # Changement de related_name

    object_id = models.PositiveIntegerField(null=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.name} ({self.get_media_type_display()})"

    def get_media_type_display(self):
        return dict(self.MEDIA_TYPES).get(self.media_type, self.media_type)


# Modèle Livre spécifique à l'application `staff`
class BookStaff(MediaStaff):
    author = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        if not self.media_type:
            self.media_type = 'book'
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(BookStaff)
        super().save(*args, **kwargs)


# Modèle DVD spécifique à l'application `staff`
class DVDStaff(MediaStaff):
    producer = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        if not self.media_type:
            self.media_type = 'dvd'
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(DVDStaff)
        super().save(*args, **kwargs)


# Modèle CD spécifique à l'application `staff`
class CDStaff(MediaStaff):
    artist = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        if not self.media_type:
            self.media_type = 'cd'
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(CDStaff)
        super().save(*args, **kwargs)


# Modèle Jeu de Plateau spécifique à l'application `staff`
class BoardGameStaff(MediaStaff):
    creators = models.CharField(max_length=100)
    is_visible = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    game_type = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

    def toggle_availability(self):
        with transaction.atomic():
            if not StaffBorrow.objects.filter(media=self, is_returned=False).exists():
                self.is_available = not self.is_available
                self.save(update_fields=['is_available'])

    @staticmethod
    def can_borrow():
        return False  # Les jeux de plateau ne peuvent pas être empruntés

    def save(self, *args, **kwargs):
        if not self.media_type:
            self.media_type = 'board_game'
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(BoardGameStaff)
        super().save(*args, **kwargs)
