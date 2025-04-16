from django.shortcuts import render, redirect, get_object_or_404
from .models import Borrow, Member, Media, Livre, DVD, CD, JeuPlateau, BorrowingRule
from .forms import MediaForm, MemberForm
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import JsonResponse
from .services.borrow_service import borrow_media, return_media
from .services.borrowing_rules_service import get_active_borrowing_rules
from .services.member_service import add_member, update_member as update_member_service
from personnel.services.member_service import delete_member


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    success_url = reverse_lazy('index')


# Page d'accueil pour afficher les différentes actions disponibles pour le personnel
def index(request):
    borrows = Borrow.objects.all()
    members = Member.objects.all()
    context = {
        'members': members,
    }
    return render(request, 'personnel/index.html', {'borrows': borrows, 'members': members})


def handle_form_errors(request, form):
    """Gestion des erreurs de formulaire."""
    for field in form:
        if field.errors:
            for error in field.errors:
                messages.error(request, f"Erreur dans le champ '{field.label}': {error}")


# Vérifie si l'utilisateur est staff
def is_staff(user):
    return user.is_staff

# Page de permission refusée
def permission_denied_view(request):
    return render(request, '403.html', status=403)

# Ajout d'un média
@login_required
@user_passes_test(is_staff, login_url='no_permission')
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
            }

            # Définir le mappage des champs spécifiques à chaque type de média
            media_fields_mapping = {
                'livre': {'model': Livre, 'specific_field': 'author'},
                'dvd': {'model': DVD, 'specific_field': 'producer'},
                'cd': {'model': CD, 'specific_field': 'artist'},
                'jeu_plateau': {'model': JeuPlateau, 'specific_field': 'creators', 'game_type': True},
            }

            # Vérifier si le media_type existe dans notre mappage
            if media_type in media_fields_mapping:
                media_info = media_fields_mapping[media_type]
                model_class = media_info['model']
                specific_field = media_info['specific_field']

                # Gérer les champs spécifiques en fonction du type de média
                specific_value = form.cleaned_data[specific_field]

                # Cas spécifique pour 'jeu_plateau' avec le champ 'game_type'
                if media_type == 'jeu_plateau':
                    # Vérification explicite pour le champ 'creators' qui est requis pour 'jeu_plateau'
                    if not form.cleaned_data.get('creators'):
                        form.add_error('creators', 'This field is required.')
                        return render(request, 'personnel/add_media.html', {'form': form})

                    if 'game_type' in form.cleaned_data:
                        game_type = form.cleaned_data['game_type']
                    else:
                        messages.error(request, "Le champ 'game_type' est manquant.")
                        return render(request, 'personnel/add_media.html', {'form': form})

                    media_instance = model_class.objects.create(
                        name=form.cleaned_data['name'],
                        available=form.cleaned_data['available'],
                        creators=specific_value,
                        game_type=game_type
                    )
                elif media_type == 'livre':
                    specific_value = form.cleaned_data[specific_field]
                    media_instance = model_class.objects.create(
                        name=form.cleaned_data['name'],
                        available=form.cleaned_data['available'],
                        author=specific_value
                    )
                elif media_type == 'cd':
                    specific_value = form.cleaned_data[specific_field]
                    media_instance = model_class.objects.create(
                        name=form.cleaned_data['name'],
                        available=form.cleaned_data['available'],
                        artist=specific_value
                    )
                elif media_type == 'dvd':
                    specific_value = form.cleaned_data[specific_field]
                    media_instance = model_class.objects.create(
                        name=form.cleaned_data['name'],
                        available=form.cleaned_data['available'],
                        producer=specific_value
                    )

                messages.success(request, f"{media_instance.name} a été ajouté avec succès!")
                return redirect('media_list')

            else:
                messages.error(request, "Le type de média est invalide.")
                return redirect('add_media')

        else:
            # Gérer les erreurs du formulaire
            handle_form_errors(request, form)
            return render(request, 'personnel/add_media.html', {'form': form})

    else:
        # Afficher le formulaire si la requête est de type GET
        form = MediaForm()

    return render(request, 'personnel/add_media.html', {'form': form})


# Liste des médias
@login_required
@user_passes_test(is_staff, login_url='no_permission')
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


# Détails des médias
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def media_detail(request, pk):
    if not request.user.is_staff:  # Ceci n'est plus nécessaire
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    media = get_object_or_404(Media, pk=pk)
    return render(request, 'personnel/media_detail.html', {'media': media})


# Emprunter un média
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def borrowing_media(request):
    if not request.user.is_staff:  # Ceci n'est plus nécessaire
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    try:
        member = request.user.member
    except Member.DoesNotExist:
        return redirect('member_error')

    if request.method == 'POST':
        media_id = request.POST.get('media_id')
        if not media_id:
            messages.error(request, "Aucun média sélectionné.")
            return redirect('media_list')

        try:
            selected_media = Media.objects.get(id=media_id)
            valid, error_message = member.check_borrow_criteria(selected_media)
            if not valid:
                messages.error(request, error_message)
                return redirect('media_list')

            # Créer l'emprunt
            borrow = Borrow.objects.create(
                borrower=member,
                media=selected_media,
                user=request.user,
            )
            borrow.confirm_borrow()  # Confirmation de l'emprunt et mise à jour de la disponibilité du média

            messages.success(request, f"L'emprunt de {selected_media.name} a été effectué avec succès!")
            return redirect('borrowing_success')

        except BorrowingError as e:
            messages.error(request, str(e))
        except Media.DoesNotExist:
            messages.error(request, "Média non trouvé.")
    else:
        available_media = Media.objects.filter(available=True)
        borrows = Borrow.objects.filter(borrower=member).select_related('media')
        return render(request, 'personnel/borrowing_media.html', {
            'available_media': available_media,
            'borrows': borrows,
            'member': member,
        })



# Règles d'emprunt d'un média
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def view_borrowing_rules(request):
    if not request.user.is_staff:  # Ceci n'est plus nécessaire
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    rules = get_active_borrowing_rules()
    return render(request, 'personnel/borrowing_rules.html', {'rules': rules})


# Retourner un emprunt
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def returning_media_view(request, borrow_id):
    if not request.user.is_staff:  # Ceci n'est plus nécessaire
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    try:
        member = request.user.member
    except Member.DoesNotExist:
        return redirect('member_error')
    return return_media(borrow_id, member)


# Pour choisir quel emprunt retourner
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def choose_borrow_to_return_view(request):
    if not request.user.is_staff:  # Ceci n'est plus nécessaire
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    try:
        member = request.user.member
    except Member.DoesNotExist:
        return redirect('member_error')
    borrows = get_borrows_to_return(member)
    return render(request, 'personnel/returning_media.html', {'borrows': borrows})


#Filtre les emprunts d'une membre pour retourner ceux qui n'ont pas été retournés
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def get_borrows_to_return(member):
    if not request.user.is_staff:  # Ceci n'est plus nécessaire
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    return Borrow.objects.filter(borrower=member, date_effective_return__isnull=True)


# Ajout d'un membre
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def add_member_view(request):
    if not request.user.is_staff:  # Ceci n'est plus nécessaire
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            try:
                member = add_member(form)
                messages.success(request, "Membre ajouté avec succès!")
                return redirect('member_detail', pk=member.pk)
            except MemberAlreadyExistsError as e:
                messages.error(request, f"Erreur : {e}")
            except ValueError as e:
                messages.error(request, f"Erreur : {e}")
            except Exception as e:
                messages.error(request, f"Erreur inconnue : {str(e)}")
        else:
            handle_form_errors(request, form)
    else:
        form = MemberForm()

    return render(request, 'personnel/add_member.html', {'form': form})


# Afficher la liste des membres
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def member_list_view(request):
    if not request.user.is_staff:  # Ceci n'est plus nécessaire
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    members = Member.objects.all()
    return render(request, 'personnel/member_list.html', {'members': members})


# Afficher les détails d'un membre (vue de lecture seule)
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def member_detail_view(request, pk):
    if not request.user.is_staff:  # Ceci n'est plus nécessaire
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    member = get_object_or_404(Member, pk=pk)
    return render(request, 'personnel/member_detail.html', {'member': member})


# Mettre à jour un membre via une vue dédiée
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def update_member_view(request, pk):
    if not request.user.is_staff:  # Ceci n'est plus nécessaire
        raise PermissionDenied("Vous n'avez pas les droits nécessaires.")

    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            try:
                update_member_service(member, form.cleaned_data)
                messages.success(request, "Le membre a été mis à jour avec succès!")
                return redirect('member_detail', pk=member.pk)
            except Exception as e:
                messages.error(request, f"Une erreur est survenue : {str(e)}")
        else:
            messages.error(request, "Le formulaire n'est pas valide.")
    else:
        form = MemberForm(instance=member)

    return render(request, 'personnel/update_member.html', {'form': form, 'member': member})


# Suppression d'un membre
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def delete_member_view(request, pk):
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

    return redirect('member_list')  # Rediriger vers la liste des membres


# Vérification si un membre a du retard
@login_required
@user_passes_test(is_staff, login_url='no_permission')
def members_overdue(request):
    # Filtrer les membres qui ont des emprunts en retard
    overdue_members = Member.objects.filter(
        borrow__return_date__lt=timezone.now(),
        borrow__returned=False
    ).distinct()

    return render(request, 'personnel/members_overdue.html', {'overdue_members': overdue_members})

def member_error():
    return render(request, 'personnel/member_error.html')

