from django import forms
from .models import Media, Member




# forms.py
class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['name', 'media_type']



class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name', 'email','date_of_birth', 'address', 'phone_number', 'blocked']


