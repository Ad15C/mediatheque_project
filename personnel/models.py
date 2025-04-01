from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# Modèle Membre
class Member(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    blocked = models.BooleanField(default=False)

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

    def __str__(self):
        return f"{self.name} ({self.get_media_type_display()})"


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

    def __str__(self):
        return self.name


# Modèle Emprunt
class Borrow(models.Model):
    borrower = models.ForeignKey(Member, on_delete=models.CASCADE)
    date_borrowed = models.DateField(default=timezone.now)
    date_due = models.DateTimeField(default=default_due_date)
    date_effective_return = models.DateField(null=True, blank=True)


    # Champs pour le contenu générique (livre, DVD, CD)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    media = GenericForeignKey('content_type', 'object_id')

    objects = models.Manager()

    def __str__(self):
        return f"Emprunt de {self.media} par {self.borrower} - {'En retard' if self.is_late() else 'En cours'}"


    def clean(self):
        """Validation des règles d'emprunt"""
        if not self.borrower:
            raise ValidationError("Un emprunteur est requis pour cet emprunt.")

        borrower = self.borrower  # Accès explicite à l'instance Member

        if borrower.blocked:
            raise ValidationError("Cet emprunteur est bloqué.")

        if borrower.got_delayed():
            raise ValidationError("L'emprunteur a un emprunt en retard.")

        if borrower.currently_borrowed() >= 3:
            raise ValidationError("Un emprunteur ne peut pas avoir plus de 3 emprunts en même temps.")

        if isinstance(self.media, JeuPlateau):
            raise ValidationError("Les jeux de plateau ne peuvent pas être empruntés.")

        if not self.media or not getattr(self.media, 'available', False):
            raise ValidationError("Ce média n'est pas disponible.")

    def is_late(self):
        """Vérifie si l'emprunteur est en retard"""
        return self.date_effective_return is None and self.date_due is not None and timezone.now() > self.date_due




