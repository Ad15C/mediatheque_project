from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from .messages import BORROW_BLOCKED, BORROW_TOO_MANY, MEDIA_NOT_AVAILABLE, MEMBER_HAS_DELAY
from django.core.cache import cache


def get_default_due_date():
    return timezone.now() + timedelta(days=7)


# Modèle Membre
class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="member")
    name = models.CharField(max_length=100)
    email = models.EmailField()
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    blocked = models.BooleanField(default=False)
    objects = models.Manager()

    def __str__(self):
        return self.name

    @property
    def currently_borrowed(self):
        cache_key = f"member_{self.id}_borrow_count"
        borrow_count = cache.get(cache_key)

        if borrow_count is None:
            borrow_count = Borrow.objects.filter(borrower=self, date_effective_return__isnull=True).count()
            cache.set(cache_key, borrow_count, timeout=60 * 15)

        return borrow_count

    def has_borrowing_limit_exceeded(self):
        limit = BorrowingRule.get_active_limit()
        return self.currently_borrowed >= limit

    def is_overdue(self):
        cache_key = f"member_{self.id}_overdue"
        overdue = cache.get(cache_key)

        if overdue is None:
            overdue = Borrow.objects.filter(
                borrower=self,
                date_effective_return__isnull=True,
                date_due__lt=timezone.now()
            ).exists()
            cache.set(cache_key, overdue, timeout=60 * 15)

        return overdue

    @classmethod
    def get_active_limit(cls):
        rule = BorrowingRule.objects.filter(active=True).first()
        return rule.value if rule else 3

    def check_borrow_criteria(self, selected_media):
        """Vérifie les critères d'emprunt du membre."""
        # 1. Le membre est-il bloqué ?
        if self.blocked:
            return False, BORROW_BLOCKED

        # 2. Le membre a-t-il des emprunts en retard ?
        if self.is_overdue():
            overdue_borrows = Borrow.objects.filter(
                borrower=self,
                date_effective_return__isnull=True,
                date_due__lt=timezone.now()
            )
            overdue_details = "\n".join([f"{borrow.media} - Due: {borrow.date_due}" for borrow in overdue_borrows])
            return False, f"{MEMBER_HAS_DELAY}\n\nEmprunts en retard :\n{overdue_details}"

        # 3. Le média est-il disponible ?
        if not selected_media.available:
            return False, MEDIA_NOT_AVAILABLE

        # 4. Le membre a-t-il atteint la limite d'emprunts ?
        limit = BorrowingRule.get_active_limit()
        if self.currently_borrowed >= limit:
            return False, BORROW_TOO_MANY.format(current_borrows=self.currently_borrowed, limit=limit)

        # 5. Vérification spécifique du type de média
        if isinstance(selected_media, JeuPlateau):
            return False, "Les jeux de plateau ne peuvent pas être empruntés."

        return True, None


# Fonction pour récupérer ContentType à la volée
def get_default_content_type():
    return ContentType.objects.get_for_model(Media).id


# Modèle Media
class Media(models.Model):
    TYPE_CHOICES = [
        ('livre', 'Livre'),
        ('dvd', 'DVD'),
        ('cd', 'CD'),
        ('jeu_plateau', 'Jeu de Plateau'),
    ]

    name = models.CharField(max_length=200)
    available = models.BooleanField(default=True)
    media_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    borrows = GenericRelation('Borrow', related_query_name='media')

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        default=get_default_content_type
    )

    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = models.Manager()

    def __str__(self):
        return f"{self.name} ({self.get_media_type_display()})"


# Modèle Livre
class Livre(Media):
    author = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        self.media_type = 'livre'
        super().save(*args, **kwargs)


# Modèle DVD
class DVD(Media):
    producer = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        self.media_type = 'dvd'
        super().save(*args, **kwargs)


# Modèle CD
class CD(Media):
    artist = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        self.media_type = 'cd'
        super().save(*args, **kwargs)


# Modèle Jeu de plateau
class JeuPlateau(models.Model):
    name = models.CharField(max_length=100)
    creators = models.CharField(max_length=100)
    is_visible = models.BooleanField(default=True)
    available = models.BooleanField(default=False)
    game_type = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

    def is_available(self):
        return self.available

    def toggle_availability(self):
        self.available = not self.available
        self.save()


# Représente un emprunt concret effectué par un membre
class Borrow(models.Model):
    borrower = models.ForeignKey(Member, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_borrowed = models.DateField(default=timezone.now)
    date_due = models.DateTimeField(default=get_default_due_date)
    date_effective_return = models.DateField(null=True, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    media = GenericForeignKey('content_type', 'object_id')

    objects = models.Manager()

    def __str__(self):
        return f"Emprunt de {self.media} par {self.borrower} - {'En retard' if self.is_late() else 'En cours'}"

    def clean(self):
        errors = []

        # Vérification des critères d'emprunt du membre
        valid, error_message = self.borrower.check_borrow_criteria(self.media)
        if not valid:
            errors.append(error_message)

        # Vérification si c'est un jeu de plateau, qui ne peut pas être emprunté
        if isinstance(self.media, JeuPlateau):
            errors.append("Les jeux de plateau ne peuvent pas être empruntés.")

        # Si des erreurs existent, les lever
        if errors:
            raise ValidationError(errors)

    def confirm_borrow(self):
        if self.media and self.media.available:
            self.media.available = False
            self.user = self.borrower.user
            self.media.save()
            self.save()

            # Invalidation du cache du nombre d'emprunts du membre
            cache.delete(f"member_{self.borrower.id}_borrow_count")

    def is_late(self):
        return self.date_effective_return is None and self.date_due is not None and timezone.now() > self.date_due

    def mark_as_returned(self):
        if self.date_effective_return:
            raise ValidationError("Ce média a déjà été retourné.")

        self.date_effective_return = timezone.now()
        self.media.available = True
        self.media.save()
        self.save()

        # Invalidation du cache du nombre d'emprunts du membre
        cache.delete(f"member_{self.borrower.id}_borrow_count")


# Représente une règle générale
class BorrowingRule(models.Model):
    rule_name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    value = models.IntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    limit = models.PositiveIntegerField(default=3)
    objects = models.Manager()

    def __str__(self):
        return self.description

    @classmethod
    def get_active_limit(cls):
        """
        Retourne la limite d'emprunts active si elle existe, sinon retourne 3 par défaut.
        """
        rule = cls.objects.filter(active=True).first()
        return rule.value if rule else 3
    pass

