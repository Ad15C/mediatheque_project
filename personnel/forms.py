from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
import re
from .models import Media, Member, JeuPlateau, Livre, DVD, CD


# forms.py
class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['name', 'media_type', 'available']

    # Champs supplémentaires pour chaque type de média
    author = forms.CharField(required=False, max_length=200)
    producer = forms.CharField(required=False, max_length=200)
    artist = forms.CharField(required=False, max_length=200)
    creators = forms.CharField(required=False, max_length=200)
    game_type = forms.CharField(required=False, max_length=200)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        media_type = self.data.get('media_type', self.initial.get('media_type', 'livre'))

        # Ajuster les champs en fonction du type de média
        if media_type == 'livre':
            self.fields['author'].required = True
        elif media_type == 'dvd':
            self.fields['producer'].required = True
        elif media_type == 'cd':
            self.fields['artist'].required = True
        elif media_type == 'jeu_plateau':
            self.fields['creators'].required = True
            self.fields['game_type'].required = True

    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get('media_type')

        # Vérification de l'existence de media_type et validation des champs en fonction du type
        if media_type:
            if media_type == 'livre' and not cleaned_data.get('author'):
                raise forms.ValidationError('L\'auteur est requis pour un livre.')
            elif media_type == 'dvd' and not cleaned_data.get('producer'):
                raise forms.ValidationError('Le producteur est requis pour un DVD.')
            elif media_type == 'cd' and not cleaned_data.get('artist'):
                raise forms.ValidationError('L\'artiste est requis pour un CD.')
            elif media_type == 'jeu_plateau' and not cleaned_data.get('creators'):
                raise forms.ValidationError('Les créateurs sont requis pour un jeu de plateau.')
            elif media_type == 'jeu_plateau' and not cleaned_data.get('game_type'):
                raise forms.ValidationError('Le type de jeu est requis pour un jeu de plateau.')

        return cleaned_data


# MemberForm avec validation des emails et gestion des mots de passe
class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name', 'email', 'date_of_birth', 'address', 'phone_number', 'blocked']

    # Champ Username pour l'utilisateur associé
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    email = forms.EmailField(max_length=254, required=True)

    # Champ pour la confirmation du mot de passe
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Member.objects.filter(email=email).exists():
            raise ValidationError('Un membre avec cet email existe déjà. Veuillez en choisir un autre.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Un utilisateur avec ce nom d\'utilisateur existe déjà. Veuillez en choisir un autre.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        # Vérification que le mot de passe et la confirmation du mot de passe correspondent
        if password != password_confirm:
            raise ValidationError('Les mots de passe ne correspondent pas.')

        # Vérification de la force du mot de passe (longueur minimale, majuscules, chiffres, etc.)
        if len(password) < 8:
            raise ValidationError('Le mot de passe doit contenir au moins 8 caractères.')

        if not re.search(r'[A-Z]', password):  # Vérifie la présence d'une majuscule
            raise ValidationError('Le mot de passe doit contenir au moins une lettre majuscule.')

        if not re.search(r'[0-9]', password):  # Vérifie la présence d'un chiffre
            raise ValidationError('Le mot de passe doit contenir au moins un chiffre.')

        return cleaned_data

    def save(self, commit=True):
        # Créer l'utilisateur associé
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password']
        )

        # Créer l'objet 'member' sans encore le sauver dans la base de données
        member = super().save(commit=False)
        member.user = user  # Lier l'utilisateur à ce membre

        # Si commit est True, sauvegarder le membre
        if commit:
            member.save()

        return member