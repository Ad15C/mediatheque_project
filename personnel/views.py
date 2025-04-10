from django.shortcuts import render, redirect, get_object_or_404
from .models import Borrow, Member, Media, Livre, DVD, CD, JeuPlateau, BorrowingRule
from .forms import MediaForm, MemberForm
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User





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


# Fiche détail d\'un média
def media_detail(request, pk):
    media = get_object_or_404(Media, pk=pk)
    for attr in ('livre', 'dvd', 'cd'):
        if hasattr(media, attr):
            specific = getattr(media, attr)
            break
    else:
        specific = media
    return render(request, 'personnel/media_detail.html', {'media': specific})


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
    # Vérifie si l'utilisateur a un membre, sinon crée-le
    create_member_for_user(request.user)  # Créer un membre si nécessaire

    # Récupère le membre de l'utilisateur
    member = request.user.member

    available_media = Media.objects.filter(available=True)

    if request.method == 'POST':
        media_id = request.POST.get('media_id')
        try:
            selected_media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            messages.error(request, "Ce média n'existe pas.")
            return redirect('borrowing_media')

        # Vérification des critères d'emprunt via la méthode du modèle
        blocked, too_many_borrows, has_delay, media_not_available = Member.check_borrow_criteria(member, selected_media)

        if blocked:
            messages.error(request, "Cet utilisateur est bloqué.")
        elif too_many_borrows:
            messages.error(request,
                           f"Vous avez déjà {member.currently_borrowed()} emprunts. La limite est de {BorrowingRule.get_active_limit()} emprunts.")
        elif has_delay:
            messages.error(request, "Vous avez un emprunt en retard.")
        elif media_not_available:
            messages.error(request, "Ce média n'est pas disponible.")
        else:
            # Création de l'emprunt
            borrow = Borrow(
                borrower=member,
                media=selected_media,
                content_type=ContentType.objects.get_for_model(selected_media),
                object_id=selected_media.id
            )
            try:
                borrow.clean()  # Validation des règles d'emprunt
                borrow.confirm_borrow()  # Effectue l'emprunt et marque le média comme emprunté
                borrow_success = True
                messages.success(request, f"L'emprunt de {selected_media.name} a été effectué avec succès.")
            except ValidationError as e:
                messages.error(request, str(e))

        return render(request, 'personnel/borrowing_media.html', {
            'available_media': available_media,
            'member': member,
            'borrow_success': borrow_success,
        })

    return render(request, 'personnel/borrowing_media.html', {'available_media': available_media, 'member': member})


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

    if borrow.date_effective_return:
        messages.error(request, f"Le média {borrow.media.name} a déjà été retourné.")
        return redirect('choose_borrow')

    if request.method == "POST":
        borrow.return_media()  # Assurez-vous que cette méthode met à jour les champs nécessaires
        messages.success(request, f"Le média {borrow.media.name} a été retourné et est maintenant disponible.")
        return redirect('choose_borrow')

    return render(request, 'personnel/returning_media.html', {'borrow': borrow})


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

            """ Vérifie si un utilisateur existe déjà avec ce mail"""
            user, created = User.objects.get_or_create(
                username=email,
                defaults={'email': email, 'password': make_password('defaultpassword')}
            )

            """Créer le membre et l'associer à l'utilisateur"""
            member = form.save(commit=False)
            member.user = user
            member.save()

            return redirect('member_list')
    else:
        form = MemberForm()

    return render(request, 'personnel/add_member.html', {'form': form})


# Afficher la liste des membres
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
def delete_member(request, member_id):
    member = get_object_or_404(Member, id=member_id)

    """ Vérifier que l'utilisateur est un administrateur """
    if not request.user.is_staff:
        raise PermissionDenied

    member.delete()
    return redirect('member_list')


def member_error(request):
    return render(request, 'personnel/member_error.html')
