from django import forms
from .models import Media, Member




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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si le formulaire a déjà un media_type sélectionné, utilisez-le
        media_type = self.data.get('media_type', self.initial.get('media_type', 'livre'))

        # Afficher les champs appropriés en fonction du type de média
        if media_type == 'livre':
            self.fields['author'].required = True
        elif media_type == 'dvd':
            self.fields['producer'].required = True
        elif media_type == 'cd':
            self.fields['artist'].required = True
        elif media_type == 'jeu_plateau':
            self.fields['creators'].required = True

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

        return cleaned_data





class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name', 'email', 'date_of_birth', 'address', 'phone_number', 'blocked']

    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)


