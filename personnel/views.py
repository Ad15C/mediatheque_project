from django.shortcuts import render, redirect, get_object_or_404
from .models import Borrow, Member, Media, Livre, DVD, CD, JeuPlateau, BorrowingRule
from .forms import MediaForm, MemberForm
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .messages import  BORROW_BLOCKED, BORROW_TOO_MANY, MEDIA_NOT_AVAILABLE
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import Http404




class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    success_url = reverse_lazy('index')

# Page d'accueil pour afficher les différentes actions disponibles pour le personnel
def index(request):
    borrows = Borrow.objects.all()
    members = Member.objects.all()
    return render(request, 'personnel/index.html', {'borrows': borrows, 'members': members})


# Liste des médias
def media_list(request):
    livres = Livre.objects.all().order_by('name')
    dvds = DVD.objects.all().order_by('name')
    cds = CD.objects.all().order_by('name')
    jeux_plateau = JeuPlateau.objects.all().order_by('name')

    return render(request, 'personnel/media_list.html', {
        'livres': livres,
        'dvds': dvds,
        'cds': cds,
        'jeux_plateau': jeux_plateau
    })


# Details des médias
@login_required
def media_detail(request, pk):
    try:
        media = Livre.objects.get(pk=pk)
    except Livre.DoesNotExist:
        try:
            media = DVD.objects.get(pk=pk)
        except DVD.DoesNotExist:
            try:
                media = CD.objects.get(pk=pk)
            except CD.DoesNotExist:
                media = JeuPlateau.objects.get(pk=pk)

    return render(request, 'personnel/media_detail.html', {'media': media})



# Ajout d'un média
@login_required
def add_media(request):
    if request.method == 'POST':
        form = MediaForm(request.POST)
        if form.is_valid():
            media_type = form.cleaned_data['media_type']
            # En fonction du type de média, créer l'objet correspondant
            if media_type == 'livre':
                Livre.objects.create(
                    name=form.cleaned_data['name'],
                    available=form.cleaned_data['available'],
                    media_type=media_type,
                    author=form.cleaned_data['author'],
                )
            elif media_type == 'dvd':
                DVD.objects.create(
                    name=form.cleaned_data['name'],
                    available=form.cleaned_data['available'],
                    media_type=media_type,
                    producer=form.cleaned_data['producer'],
                )
            elif media_type == 'cd':
                CD.objects.create(
                    name=form.cleaned_data['name'],
                    available=form.cleaned_data['available'],
                    media_type=media_type,
                    artist=form.cleaned_data['artist'],
                )
            elif media_type == 'jeu_plateau':
                JeuPlateau.objects.create(
                    name=form.cleaned_data['name'],
                    creators=form.cleaned_data['creators'],
                )

            return redirect('media_list')
    else:
        form = MediaForm()

    return render(request, 'personnel/add_media.html', {'form': form})




# Emprunter un média
@login_required
def borrowing_media(request):
    member = request.user.member

    if request.method == 'POST':
        media_id = request.POST.get('media_id')
        if not media_id:
            messages.error(request, "Aucun média sélectionné.")
            return redirect('media_list')  # Rediriger vers la liste des médias

        selected_media = Media.objects.get(id=media_id)

        # Vérification des critères d'emprunt
        can_borrow, error_message = Member.check_borrow_criteria(member, selected_media)

        if can_borrow:
            messages.error(request, error_message)  # Affiche le message d'erreur approprié
        else:
            try:
                # Si l'emprunt est possible, créer un nouvel emprunt
                borrow = Borrow(
                    borrower=member,
                    content_type=ContentType.objects.get_for_model(selected_media),
                    object_id=selected_media.id
                )
                borrow.clean()  # Validation des règles d'emprunt
                borrow.confirm_borrow()  # Confirme l'emprunt
                messages.success(request, f"L'emprunt de {selected_media.name} a été effectué avec succès.")
            except ValidationError as e:
                messages.error(request, str(e))

    # Liste des médias disponibles pour l'emprunt
    available_media = Media.objects.filter(available=True)
    borrows = Borrow.objects.filter(borrower=member)

    return render(request, 'personnel/borrowing_media.html')


    # Règles d'emprunt d'un média
def borrowing_rules(request):
    rules = BorrowingRule.objects.filter(active=True)
    return render(request, 'personnel/borrowing_rules.html', {'rules': rules})


def check_borrow_criteria(member, selected_media):
    blocked = member.blocked
    has_delay = member.got_delayed()
    media_not_available = not selected_media.available
    limite = BorrowingRule.get_active_limit()
    too_many_borrows = member.currently_borrowed() >= limite
    return blocked, too_many_borrows, has_delay, media_not_available




# Retourner un emprunt
@login_required
def returning_media(request, borrow_id):
    borrow = get_object_or_404(Borrow, id=borrow_id)

    """Vérifie si le média a déjà été retourné"""
    if borrow.date_effective_return:
        messages.error(request, "Ce média a déjà été retourné.")
        return redirect('choose_borrow_to_return')
    if borrow.borrower != member:
        raise PermissionDenied("Vous ne pouvez pas retourner ce média.")

    """Marquer la date de retour"""
    borrow.date_effective_return = timezone.now()

    """Rendre le média disponible à nouveau"""
    media = borrow.media  # Utilisez la relation entre Borrow et Media
    if media:
        media.available = True
        media.save()

    """Sauvegarder les modifications de l'emprunt"""
    borrow.save()

    messages.success(request, f"Le média {media.name} a été retourné avec succès.")
    return redirect('choose_borrow_to_return')



# Pour choisir quel emprunt retourner
@login_required
def choose_borrow_to_return(request):
    borrows = Borrow.objects.filter(date_effective_return__isnull=True)
    return render(request, 'personnel/returning_media.html', {'borrows': borrows})


def create_member_for_user(user):
    """Cette fonction crée un membre si l'utilisateur n'en a pas encore."""
    if not hasattr(user, 'member'):
        member = Member(user=user)
        member.save()


# Ajout d'un membre
@login_required
def add_member(request):
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Vérifie si un utilisateur existe déjà avec cet email
            user, created = User.objects.get_or_create(
                username=email,
                defaults={'email': email, 'password': make_password('defaultpassword')}
            )

            # Vérifie si un membre existe déjà pour cet utilisateur
            if not Member.objects.filter(user=user).exists():
                # Créer le membre s'il n'en existe pas déjà un
                member = form.save(commit=False)
                member.user = user
                member.save()

            return redirect('member_list')
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
def member_detail(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    return render(request, 'personnel/member_detail.html', {'member': member})


# Mettre à jour un Membre existant
@login_required
def update_member(request, member_id):
    """ Récupérer le membre avec l'ID """
    member = get_object_or_404(Member, id=member_id)

    """ Si la requête est POST, cela signifie que l'utilisateur souhaite sauvegarder les modifications """
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            """  Rediriger vers la page des détails après la mise à jour"""
            messages.success(request, "Les informations du membre ont été mises à jour.")
            return redirect('member_detail', member_id=member.id)
    else:
        """ Pré-remplir le formulaire avec les données du membre"""
        form = MemberForm(instance=member)

    return render(request, 'personnel/update_member.html', {'form': form, 'member': member})



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

    return redirect('member_list')


def member_error(request):
    return render(request, 'personnel/member_error.html')
