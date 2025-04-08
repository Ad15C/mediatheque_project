from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator
from django.db.models.manager import Manager



# Modèle Membre
class Member(models.Model):
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

    name= models.CharField(max_length=200)
    available=models.BooleanField(default=True)
    media_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
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
    name=models.CharField(max_length=200)
    creators=models.CharField(max_length=200)
    objects = models.Manager()

    def __str__(self):
        return self.name


# Représente un emprunt concret effectué par un membre
class Borrow(models.Model):
    borrower = models.ForeignKey(Member, on_delete=models.CASCADE)
    date_borrowed = models.DateField(default=timezone.now)
    date_due = models.DateTimeField(default=default_due_date)
    date_effective_return = models.DateField(null=True, blank=True)
    objects = models.Manager()


    """ Champs pour le contenu générique (livre, DVD, CD) """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    media = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"Emprunt de {self.media} par {self.borrower} - {'En retard' if self.is_late() else 'En cours'}"

    def clean(self):
        """Validation des règles d'emprunt"""
        if not self.borrower:
            raise ValidationError("Un emprunteur est requis pour cet emprunt.")

        borrower = self.borrower

        if borrower.blocked:
            raise ValidationError("Cet emprunteur est bloqué.")

        if borrower.got_delayed():
            raise ValidationError("L'emprunteur a un emprunt en retard.")

        limite = BorrowingRule.get_active_limit()
        if borrower.currently_borrowed() >= limite:
            raise ValidationError(f"Un emprunteur ne peut pas avoir plus de {limite} emprunts en même temps.")

        if isinstance(self.media, JeuPlateau):
            raise ValidationError("Les jeux de plateau ne peuvent pas être empruntés.")

        if not self.media or not getattr(self.media, 'available', False):
            raise ValidationError("Ce média n'est pas disponible.")


    """ Rend le média disponible et enregistre l'emprunt """
    def confirm_borrow(self):
        if not self.media.available:
            raise ValidationError("Le média n'est plus disponible.")
        """ Marquer le média comme non disponible """
        self.media.available = False
        self.media.save()

        self.save()

    """ Vérifie si l'emprunteur est en retard """
    def is_late(self):
        return self.date_effective_return is None and self.date_due is not None and timezone.now() > self.date_due


    """ Met à jour les date de retour et rend le média à nouveau disponible """
    def return_media(self):
        self.date_effective_return = timezone.now()
        if hasattr(self.media, 'available'):
            self.media.available = True
            self.media.save()
        self.save()


# Représente une règle générale
class BorrowingRule(models.Model):
    rule_name = models.CharField(max_length=100)
    description = models.TextField()
    value = models.IntegerField(validators=[MaxValueValidator(10)])  # par exemple, max = 10
    active = models.BooleanField(default=True)
    objects: Manager['BorrowingRule'] = models.Manager()

    def __str__(self):
        return self.rule_name

    @classmethod
    def get_active_limit(cls):
        """Retourne la valeur de la règle active ou 3 si aucune n'est définie."""
        rule = cls.objects.filter(active=True).first()
        return rule.value if rule else 3


