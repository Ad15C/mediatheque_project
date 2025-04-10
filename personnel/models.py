from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models.manager import Manager
from django.contrib.auth.models import User




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
        """Vérifie si un membre peut emprunter un média en fonction des règles actives."""
        blocked = member.blocked
        has_delay = member.got_delayed()
        media_not_available = not selected_media.available

        # Limite d'emprunt active
        limite = BorrowingRule.get_active_limit()

        # Vérifie si le membre a dépassé la limite d'emprunts
        too_many_borrows = member.currently_borrowed() >= limite

        # Autres validations selon la logique métier
        if isinstance(selected_media, JeuPlateau):
            messages.error(request, "Les jeux de plateau ne peuvent pas être empruntés.")
            return redirect('borrowing_media')

        return blocked, too_many_borrows, has_delay, media_not_available


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


