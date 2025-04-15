from django.shortcuts import render, redirect, get_object_or_404
from .models import Borrow, Member, Media, Livre, DVD, CD, JeuPlateau, BorrowingRule
from .forms import MediaForm, MemberForm
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .messages import BORROW_BLOCKED, BORROW_TOO_MANY, MEDIA_NOT_AVAILABLE, BORROW_SUCCESS
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseForbidden, HttpResponseNotFound
from django.db import transaction
from django.utils import timezone
from django.apps import apps
from .services.borrow_service import validate_borrowing, get_borrows_to_return,return_media
from .services.borrowing_rules_service import  get_active_borrowing_rules, get_member_borrowing_rule
from .services.member_service import delete_member
from .services.member_service import update_member as update_member_service
from personnel.services.member_service import add_member


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    success_url = reverse_lazy('index')


# Page d'accueil pour afficher les différentes actions disponibles pour le personnel
def index(request):
    borrows = Borrow.objects.all()
    members = Member.objects.all()
    return render(request, 'personnel/index.html', {'borrows': borrows, 'members': members})


# Ajout d'un média
@login_required
def add_media(request):
    if not request.user.is_staff:
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    if request.method == 'POST':
        form = MediaForm(request.POST)
        if form.is_valid():
            media_type = form.cleaned_data['media_type']
            common_fields = {
                'name': form.cleaned_data['name'],
                'available': form.cleaned_data['available'],
                'media_type': media_type,
            }

            media_classes = {
                'livre': (Livre, 'author'),
                'dvd': (DVD, 'producer'),
                'cd': (CD, 'artist'),
                'jeu_plateau': (JeuPlateau, 'game_type')
            }

            model_class, specific_field = media_classes.get(media_type, (None, None))

            if not model_class:
                messages.error(request, "Type de média invalide ou non supporté.")
                return redirect('add_media')

            model_class.objects.create(**common_fields, **{specific_field: form.cleaned_data[specific_field]})
            messages.success(request, "Média ajouté avec succès!")
            return redirect('media_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur dans le champ {field}: {error}")
    else:
        form = MediaForm()  # ✅ Défini même en GET

    return render(request, 'personnel/add_media.html', {'form': form})

#Ajout de Jeu Plateau
@login_required
def add_jeu_plateau(request):
    if request.method == 'POST':
        form = MediaForm(request.POST)
        if form.is_valid():
            JeuPlateau.objects.create(
                name=form.cleaned_data['name'],
                available=form.cleaned_data['available'],
                media_type='jeu_plateau',
                game_type=form.cleaned_data['game_type'],
            )
            messages.success(request, "Jeu de plateau ajouté avec succès!")
            return redirect('media_list')
    else:
        form = MediaForm()
    return render(request, 'personnel/add_jeu_plateau.html', {'form': form})


# Liste des médias
@login_required
def media_list(request):
    livres = Livre.objects.all().prefetch_related('borrow_set').order_by('name')
    dvds = DVD.objects.all().prefetch_related('borrow_set').order_by('name')
    cds = CD.objects.all().prefetch_related('borrow_set').order_by('name')
    jeux_plateau = JeuPlateau.objects.all().prefetch_related('borrow_set').order_by('name')
    return render(request, 'personnel/media_list.html', {
        'livres': livres,
        'dvds': dvds,
        'cds': cds,
        'jeux_plateau': jeux_plateau
    })


# Details des médias
@login_required
def media_detail(request, pk):
    media = get_object_or_404(Media, pk=pk)
    return render(request, 'personnel/media_detail.html', {'media': media})


# Emprunter un média
@login_required
def borrowing_media(request):
    try:
        member = request.user.member
    except Member.DoesNotExist:
        return redirect('member_error')
    borrow_success = False
    if request.method == 'POST':
        media_id = request.POST.get('media_id')
        if not media_id:
            messages.error(request, "Aucun média sélectionné.")
            return redirect('media_list')

        try:
            selected_media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            raise Http404("Média non trouvé.")

        # Tenter de créer un emprunt
        try:
            borrow = Borrow(borrower=member, media=selected_media)
            borrow.clean()  # Cela déclenchera la validation
            borrow.confirm_borrow()  # Valider l'emprunt

            borrow_success = True
            messages.success(request, "Emprunt effectué avec succès!")
        except ValidationError as e:
            # Capture des erreurs de validation et les affichages dans les messages
            for error in e.message_dict.values():
                for msg in error:
                    messages.error(request, msg)

    available_media = Media.objects.filter(available=True)
    borrows = Borrow.objects.filter(borrower=member).select_related('content_type', 'media')
    return render(request, 'personnel/borrowing_media.html', {
        'available_media': available_media,
        'borrows': borrows,
        'member': member,
        'borrow_success': borrow_success,
    })


# Règles d'emprunt d'un média
@login_required
def view_borrowing_rules(request):
    rules = get_active_borrowing_rules()
    return render(request, 'personnel/borrowing_rules.html', {'rules': rules})


# Retourner un emprunt
@login_required
def returning_media(request, borrow_id):
    try:
        member = request.user.member
    except Member.DoesNotExist:
        return redirect('member_error')
    return return_media(borrow_id, member)



# Pour choisir quel emprunt retourner
@login_required
def choose_borrow_to_return(request):
    try:
        member = request.user.member
    except Member.DoesNotExist:
        return redirect('member_error')
    borrows = get_borrows_to_return(member)
    return render(request, 'personnel/returning_media.html', {'borrows': borrows})


# Ajout d'un membre
@login_required
def add_member_view(request):
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            print("Form is valid:", form.cleaned_data)
            try:
                member = add_member(form)
                messages.success(request, "Membre ajouté avec succès!")
                return redirect('member_detail', pk=member.pk)
            except ValueError as e:
                messages.error(request, f"Erreur : {e}")
            except Exception as e:
                messages.error(request, f"Erreur inconnue : {str(e)}")
        else:
            print("Form errors:", form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur dans le champ {field}: {error}")
    else:
        form = MemberForm()

    return render(request, 'personnel/add_member.html', {'form': form})


# Afficher la liste des membres
@login_required
def member_list(request):
    members = Member.objects.all()
    return render(request, 'personnel/member_list.html', {'members': members})


# Fiche détaillée d'un membre
@login_required
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    return render(request, 'personnel/member_detail.html', {'member': member})


# Mettre à jour un Membre existant
@login_required
def update_member(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            update_member_service(member, form.cleaned_data)
            messages.success(request, "Membre mis à jour avec succès!")
            return redirect('member_detail', pk=member.pk)
    else:
        form = MemberForm(instance=member)
    return render(request, 'personnel/update_member.html', {'form': form})


# Suppression d'un membre
@login_required
def delete_member(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Vous n'avez pas les droits nécessaires pour supprimer un membre.")

    try:
        member = Member.objects.get(pk=pk)
        member.delete()
        messages.success(request, "Membre supprimé avec succès.")
    except Member.DoesNotExist:
        messages.error(request, "Le membre n'existe pas.")
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}")

    return redirect('member_list')


#Vérification si un membre a du retard
@login_required
def check_if_member_is_overdue(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    overdue_borrows = Borrow.objects.filter(borrower=member, date_effective_return__isnull=True, due_date__lt=timezone.now())
    if overdue_borrows.exists():
        return JsonResponse({'message': 'Le membre a des emprunts en retard.'}, status=400)
    return JsonResponse({'message': 'Le membre n\'a pas d\'emprunts en retard.'}, status=200)


def member_error(request):
    _ = request  # silence linter about unused variable
    return render(request, 'personnel/member_error.html')

