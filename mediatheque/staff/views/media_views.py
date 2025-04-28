from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib.auth import get_user_model
from django import forms
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from mediatheque.staff.models import Media, Borrow, BoardGame

User = get_user_model()
MAX_BORROW_DURATION_DAYS = 7


class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['name', 'media_type', 'available']


class BoardGameForm(forms.ModelForm):
    class Meta:
        model = BoardGame
        fields = ['name', 'creators', 'is_visible', 'is_available', 'game_type']


# Ajout d'un média
@permission_required('authentication.can_add_media', raise_exception=True)
def add_media(request):
    if request.method == 'POST':
        media_form = MediaForm(request.POST)
        if media_form.is_valid():
            # Sauvegarde du média de base
            media = media_form.save()

            # Vérifie si l'utilisateur a choisi de créer un jeu de plateau
            if 'is_board_game' in request.POST:
                board_game_form = BoardGameForm(request.POST)
                if board_game_form.is_valid():
                    # Sauvegarde du jeu de plateau associé au média
                    board_game = board_game_form.save(commit=False)
                    board_game.media = media  # Lier le jeu de plateau au média
                    board_game.save()
                    messages.success(request, "Le jeu de plateau a été ajouté avec succès.")
                else:
                    messages.error(request, "Il y a des erreurs dans le formulaire du jeu de plateau.")

            messages.success(request, "Le média a été ajouté avec succès.")
            return redirect('media_list')
    else:
        media_form = MediaForm()
        board_game_form = BoardGameForm()

    return render(request, 'staff/add_media.html', {'media_form': media_form, 'board_game_form': board_game_form})


# Emprunter un média
@permission_required('authentication.can_borrow_media', raise_exception=True)
def borrow_media(request, pk):
    if request.method == 'POST':
        media = get_object_or_404(Media, pk=pk)

        # Vérifier si le média est un BoardGame et s'il peut être emprunté
        if isinstance(media, BoardGame) and not media.can_borrow():
            messages.error(request, 'Les jeux de plateau ne peuvent pas être empruntés.')
            return redirect('media_list')

        # Vérifier si l'utilisateur a déjà 3 emprunts en cours
        if not Borrow.can_borrow(request.user):
            messages.error(request,
                           'Vous ne pouvez pas emprunter plus de 3 médias à la fois ou vous avez des emprunts en retard.')
            return redirect('media_list')

        # Calculer la date d'échéance en fonction de la constante
        due_date = timezone.now() + timezone.timedelta(days=MAX_BORROW_DURATION_DAYS)

        # Créer l'emprunt si toutes les conditions sont validées
        Borrow.objects.create(
            user=request.user,
            media=media,
            borrow_date=timezone.now(),
            due_date=due_date
        )

        # Mettre à jour la disponibilité du média
        media.available = False
        media.save()

        messages.success(request,
                         f"Le média '{media.name}' a été emprunté avec succès. Vous devez le rendre avant le {due_date.date()}.")

    return redirect('media_list')


# Détail de l'emprunt
@permission_required('authentication.can_view_borrow', raise_exception=True)
def borrow_detail(request, borrow_id):
    borrow = get_object_or_404(Borrow.objects.select_related('media'), id=borrow_id)
    return render(request, 'borrow_detail.html', {'borrow': borrow})


# Retourner un emprunt
@permission_required('authentication.can_return_media', raise_exception=True)
def return_media(request, pk):
    if request.method == 'POST':
        borrow = get_object_or_404(Borrow, pk=pk, is_returned=False)
        borrow.is_returned = True
        borrow.return_date = timezone.now()
        borrow.save()
        borrow.media.available = True
        borrow.media.save()

        messages.success(request, "Le média a été retourné avec succès.")
    return redirect('media_list')


# Liste des médias avec filtres
@permission_required('authentication.can_view_media', raise_exception=True)
def media_list(request):
    # Récupération des filtres
    media_type_filter = request.GET.get('media_type', None)
    available_filter = request.GET.get('available', None)

    medias = Media.objects.all().prefetch_related('borrow_set')

    if media_type_filter:
        medias = medias.filter(media_type=media_type_filter)

    if available_filter is not None:
        available_filter = available_filter.lower() == 'true'
        medias = medias.filter(available=available_filter)

    # Ajouter un statut d'emprunt pour chaque média
    media_status = []
    for media in medias:
        borrow = media.borrow_set.filter(is_returned=False).first()
        if borrow:
            media_status.append({
                'media': media,
                'is_borrowed': True,
                'borrower': borrow.user,
                'borrow_date': borrow.borrow_date,
                'due_date': borrow.due_date
            })
        else:
            media_status.append({
                'media': media,
                'is_borrowed': False
            })

    return render(request, 'staff/media_list.html',
                  {'media_status': media_status, 'media_type_filter': media_type_filter,
                   'available_filter': available_filter})
