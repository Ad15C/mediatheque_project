from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models.manager import Manager
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from .messages import BORROW_BLOCKED, BORROW_TOO_MANY, MEDIA_NOT_AVAILABLE, MEMBER_HAS_DELAY



# Modèle Membre
class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    blocked = models.BooleanField(default=False)
    objects = models.Manager()


    def __str__(self):
        return self.name


    def currently_borrowed(self):
        """Retourne le nombre d'emprunts non rendus"""
        return Borrow.objects.filter(borrower=self, date_effective_return__isnull=True ).count()


    def got_delayed(self):
        """Vérifie si l'utilisateur a un emprunt en retard"""
        return Borrow.objects.filter(
            borrower=self,
            date_effective_return__isnull=True,
            date_due__lt=timezone.now()
        ).exists()

    @classmethod
    def check_borrow_criteria(cls, member, selected_media):

        if member.blocked:
            return True, BORROW_BLOCKED

        if member.got_delayed():
            return True, MEMBER_HAS_DELAY

        limite = BorrowingRule.get_active_limit()
        if member.currently_borrowed() >= limite:
            return True, BORROW_TOO_MANY.format(current_borrows=member.currently_borrowed(), limit=limite)

        if not selected_media.available:
            return True, MEDIA_NOT_AVAILABLE

        if selected_media.media_type == 'jeu_plateau':
            return True, "Les jeux de plateau ne sont pas disponibles à l'emprunt."

        if selected_media.media_type != 'jeu_plateau' and (selected_media.date_due - timezone.now()).days > 7:
            return True, "La durée maximale d'emprunt est de 7 jours."

        return False, None


# Fonction pour fixer la date de retour par défaut (+7 jours)
def default_due_date():
    return timezone.now() + timedelta(days=7)




#Modèle Media
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
    objects = models.Manager()


    def __str__(self):
        return f"{self.name} ({self.get_media_type_display()})"  # type: ignore[attr-defined]


class Livre(Media):
    author=models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        self.media_type = 'livre'
        super().save(*args, **kwargs)


class DVD(Media):
    producer=models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        self.media_type = 'dvd'
        super().save(*args, **kwargs)


class CD(Media):
    artist=models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        self.media_type = 'cd'
        super().save(*args, **kwargs)


class JeuPlateau(models.Model):
    name = models.CharField(max_length=100)
    creators = models.CharField(max_length=100)
    is_visible = models.BooleanField(default=True)
    available = models.BooleanField(default=False)

    def __str__(self):
        return self.name



# Représente un emprunt concret effectué par un membre
class Borrow(models.Model):
    borrower = models.ForeignKey(Member, on_delete=models.CASCADE)  # L'emprunteur (Member)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    date_borrowed = models.DateField(default=timezone.now)  # Date de l'emprunt
    date_due = models.DateTimeField(default=default_due_date)  # Date de retour prévue
    date_effective_return = models.DateField(null=True, blank=True)  # Date de retour réelle


    """  Champs pour la relation générique"""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)  # Type de l'objet emprunté
    object_id = models.PositiveIntegerField()  # ID de l'objet emprunté
    media = GenericForeignKey('content_type', 'object_id')


    """ Un manager pour faciliter les requêtes si nécessaire"""
    objects = models.Manager()

    def __str__(self):
        return f"Emprunt de {self.media} par {self.borrower} - {'En retard' if self.is_late() else 'En cours'}"

    def clean(self):
        errors = []

        if not self.borrower:
            errors.append("Un emprunteur est requis.")

        if self.borrower.blocked:
            errors.append(BORROW_BLOCKED)

        if self.borrower.got_delayed():
            errors.append(MEMBER_HAS_DELAY)

        if self.return_date and (self.return_date - self.date_borrowed).days > 7:
            raise ValidationError("La durée d'emprunt ne peut excéder 7 jours.")

        limite = BorrowingRule.get_active_limit()
        if self.borrower.currently_borrowed() >= limite:
            errors.append(BORROW_TOO_MANY.format(current_borrows=self.borrower.currently_borrowed(), limit=limite))

        if isinstance(self.media, JeuPlateau):
            errors.append("Les jeux de plateau ne peuvent pas être empruntés.")

        if not self.media or not self.media.available:
            errors.append(MEDIA_NOT_AVAILABLE)

        if errors:
            raise ValidationError(errors)


    """ Gère l'emprunt de manière sécurisée """
    def confirm_borrow(self):
        """Effectue la vérification et marque le média comme emprunté."""
        if not self.media.available:
            raise ValidationError("Le média n'est plus disponible.")

        if Borrow.objects.filter(media=self.media, date_effective_return__isnull=True).exists():
            raise ValidationError("Le média est déjà emprunté.")

        self.media.available = False
        self.media.save()
        self.save()


    """ Vérifie si l'emprunteur est en retard """
    def is_late(self):
        return self.date_effective_return is None and self.date_due is not None and timezone.now() > self.date_due


    """ Rendre un emprunt """
    def return_media(self):
        """ Vérifier si le média a déjà été retourné"""
        if self.date_effective_return:
            raise ValidationError("Ce média a déjà été retourné.")

        """ Marquer la date de retour"""
        self.date_effective_return = timezone.now()

        """ Rendre le média disponible à nouveau"""
        if hasattr(self.media, 'available'):
            self.media.available = True
            self.media.save()

        self.save()




# Représente une règle générale
class BorrowingRule(models.Model):
    rule_name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    value = models.IntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    objects: Manager['BorrowingRule'] = models.Manager()

    def __str__(self):
        return self.description


    @classmethod
    def get_active_limit(cls):
        """Retourne la valeur de la règle active ou 3 si aucune n'est définie."""
        rule = cls.objects.filter(active=True).first()
        return rule.value if rule else 3


