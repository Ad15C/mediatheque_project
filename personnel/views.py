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
    try:
        member = request.user.member  # Essayer d'accéder au membre
    except Member.DoesNotExist:
        messages.error(request, "Ce membre n'est pas associé à un utilisateur.")
        return redirect('some_error_page')

    available_media = Media.objects.filter(available=True).exclude(media_type='jeu_plateau')
    rules = BorrowingRule.objects.filter(active=True)  # Récupérer les règles actives

    # Vérifier si l'utilisateur a déjà vu les règles, et ne pas les réafficher après emprunt
    if not request.session.get('has_seen_rules', False):
        request.session['has_seen_rules'] = False  # Initialiser si non défini (c'est une première visite)

    borrow_success = False  # Déplacer ici pour éviter la référence avant l'assignation

    if request.method == 'POST':
        media_id = request.POST.get('media_id')
        try:
            selected_media = Media.objects.get(id=media_id)
        except ObjectDoesNotExist:
            messages.error(request, "Ce média n'existe pas.")
            return redirect('borrowing_media')

        # Vérification des critères d'emprunt
        blocked, too_many_borrows, has_delay, media_not_available = check_borrow_criteria(member, selected_media)

        if not blocked and not too_many_borrows and not has_delay and not media_not_available:
            """ Créer l'emprunt ici """
            borrow = Borrow(
                borrower=member,
                media=selected_media,
                content_type=ContentType.objects.get_for_model(selected_media),
                object_id=selected_media.id
            )
            try:
                """ Validation des règles d'emprunt"""
                borrow.clean()
                borrow.confirm_borrow()
                borrow_success = True
                messages.success(request,
                                 f"L'emprunt de {selected_media.name} a été confirmé pour {member.user.username}.")

                """ Une fois l'emprunt réussi, marquer que les règles ont été vues """
                request.session['has_seen_rules'] = True
            except ValidationError as e:
                messages.error(request, str(e))

            return render(request, 'personnel/borrowing_media.html', {
                'available_media': available_media,
                'selected_media': selected_media,
                'member': member,
                'borrow_success': borrow_success,
                'blocked': blocked,
                'too_many_borrows': too_many_borrows,
                'has_delay': has_delay,
                'media_not_available': media_not_available,
                'rules': rules,  # Passer les règles d'emprunt actives
            })

    return render(request, 'personnel/borrowing_media.html', {
        'available_media': available_media,
        'member': member,
        'rules': rules,
        'selected_media': None,
        'has_seen_rules': request.session.get('has_seen_rules', False),
    })



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
    if borrow_id == 0:
        messages.error(request, "Aucun emprunt valide n’a été sélectionné.")
        return redirect('borrowing_media')

    borrow = get_object_or_404(Borrow, id=borrow_id)

    if request.method == "POST":
        borrow.return_media()
        messages.success(request, f"Le média {borrow.media.name} a été retourné et est maintenant disponible.")
        return redirect('borrowing_media')

    return render(request, 'personnel/returning_media.html', {'borrow': borrow})


# Pour choisir quel emprunt retourner
@login_required
def choose_borrow_to_return(request):
    borrows = Borrow.objects.filter(date_effective_return__isnull=True)
    return render(request, 'personnel/returning_media.html', {'borrows': borrows})


# Afficher la liste des membres
def member_list(request):
    members = Member.objects.all()
    return render(request, 'personnel/member_list.html', {'members': members})



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


# Ajout d'un membre
@login_required
def add_member(request):
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Check if a User already exists with the same email
            user, created = User.objects.get_or_create(
                username=email,  # You can use email or another field
                defaults={'email': email, 'password': 'defaultpassword'}
            )

            # Create the member and associate with the user
            member = form.save(commit=False)
            member.user = user  # Link the user to the member
            member.save()

            # Redirect after the member is added
            return redirect('member_list')
    else:
        form = MemberForm()

    return render(request, 'personnel/add_member.html', {'form': form})


# Fiche détaillée d'un membre
@login_required
def member_detail(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    return render(request, 'personnel/member_detail.html', {'member': member})


# Suppression d'un membre
@login_required
def delete_member(request, member_id):
    member = get_object_or_404(Member, id=member_id)

    """ Vérifier que l'utilisateur est un administrateur """
    if not request.user.is_staff:
        raise PermissionDenied

    member.delete()
    return redirect('member_list')


