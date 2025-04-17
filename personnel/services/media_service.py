
def create_media(form, media_type):
    media_mapping = {
        'livre': {'model': Livre, 'specific_field': 'author'},
        'dvd': {'model': DVD, 'specific_field': 'producer'},
        'cd': {'model': CD, 'specific_field': 'artist'},
        'jeu_plateau': {'model': JeuPlateau, 'specific_field': 'creators', 'game_type': True},
    }

    if media_type not in media_mapping:
        raise ValueError("Type de média invalide.")

    media_info = media_mapping[media_type]
    model_class = media_info['model']
    specific_field = media_info['specific_field']

    media_instance = model_class.objects.create(
        name=form.cleaned_data['name'],
        available=form.cleaned_data['available'],
        **{specific_field: form.cleaned_data[specific_field]}
    )

    if media_type == 'jeu_plateau' and 'game_type' in form.cleaned_data:
        media_instance.game_type = form.cleaned_data['game_type']
        media_instance.save()

    return media_instance
