from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, LoginForm, EditProfileForm
from django.utils import timezone
from mediatheque.models import MediathequeBorrow, Media
from django.contrib.auth.models import User


@login_required
def home_view(request):
    return render(request, 'authentification/home.html')


# Inscription
def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Formulaire valide
            user = form.save()
            login(request, user)
            messages.success(request, "Inscription réussie ! Vous êtes maintenant connecté.")
            return redirect('authentification:home')
        else:
            # Afficher les erreurs pour le débogage
            print(form.errors)  # Vérifiez dans la console si l'erreur des mots de passe non correspondants est générée
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur sur {field}: {error}")
    else:
        form = CustomUserCreationForm()

    return render(request, 'authentification/signup.html', {'form': form})


# Connexion
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Vous êtes connecté avec succès.")
                if user.role == 'staff':
                    return redirect('authentification:espace_staff')  # Rediriger vers le tableau de bord staff
                else:
                    return redirect('authentification:espace_client')  # Rediriger vers le tableau de bord client
            else:
                messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
        else:
            messages.error(request, "Formulaire invalide.")
    else:
        form = LoginForm()

    return render(request, 'authentification/login.html', {'form': form})


# Déconnexion
def logout_view(request):
    logout(request)  # Déconnecte l'utilisateur
    messages.success(request, "Vous êtes maintenant déconnecté.")  # Ajoute un message de succès
    return redirect('authentification:login')


# Mise à jour du profil
@login_required
def edit_profile(request, user_id):
    # Vérifier que l'utilisateur connecté est un staff
    if not request.user.groups.filter(name="staff").exists():
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour modifier ce profil.")
        return redirect('authentification:home')

    # Récupérer l'utilisateur à modifier
    client = get_object_or_404(User, id=user_id)

    # Vérifier si l'utilisateur connecté n'essaie pas de modifier son propre profil
    if client == request.user:
        messages.error(request, "Vous ne pouvez pas modifier votre propre profil à partir d'ici.")
        return redirect('authentification:home')

    # Traiter le formulaire de modification du profil
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=client)  # Remplir avec les données de l'utilisateur à modifier
        if form.is_valid():
            form.save()  # Sauvegarder les modifications
            messages.success(request, f"Le profil de {client.username} a été mis à jour !")
            return redirect('authentification:home')  # Rediriger après la modification
        else:
            messages.error(request, "Il y a eu une erreur dans la mise à jour du profil.")
    else:
        form = EditProfileForm(
            instance=client)  # Pré-remplir le formulaire avec les données de l'utilisateur à modifier

    return render(request, 'authentification/modifier_profil.html', {'form': form, 'client': client})


# Décorateur pour vérifier que l'utilisateur est connecté
# Vue du tableau de bord client
@login_required
def client_dashboard(request):
    if not request.user.groups.filter(name='client').exists():
        return redirect('authentification:home')  # Redirige si l'utilisateur n'appartient pas au groupe 'client'

    # Récupérer les emprunts en cours pour l'utilisateur
    borrows = MediathequeBorrow.objects.filter(user=request.user, is_returned=False).select_related('media')

    # Récupérer les médias disponibles à l'emprunt
    available_media = Media.objects.filter(can_borrow=True, available=True)

    return render(request, "authentification/espace_client.html", {
        'borrows': borrows,
        'available_media': available_media
    })


# Vue du tableau de bord staff
@login_required
def staff_dashboard(request):
    if not request.user.groups.filter(name="staff").exists():
        return redirect("authentification:home")

    # Récupérer tous les emprunts en cours (avec les médias associés pour éviter des requêtes supplémentaires)
    borrows = MediathequeBorrow.objects.filter(is_returned=False).select_related('media')

    # Récupérer les emprunts en retard
    overdue_borrows = MediathequeBorrow.objects.filter(is_returned=False, due_date__lt=timezone.now()).select_related(
        'media')

    # Récupérer tous les médias (selon ton cas, tu peux envisager des filtres spécifiques pour le staff)
    all_media = Media.objects.all()

    return render(request, "authentification/espace_staff.html", {
        'borrows': borrows,
        'overdue_borrows': overdue_borrows,
        'all_media': all_media
    })
