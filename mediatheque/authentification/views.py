from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, LoginForm
from django.utils import timezone
from staff.models import Borrow, Media


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
def edit_profile(request):
    # Logique de modification du profil
    return render(request, 'authentification/edit_profile.html')


# Décorateur pour vérifier que l'utilisateur est connecté
@login_required
def client_dashboard(request):
    if not request.user.groups.filter(name='client').exists():
        return redirect('authentification:home')  # Redirige si l'utilisateur n'appartient pas au groupe 'client'

    borrows = Borrow.objects.filter(user=request.user, is_returned=False)
    available_media = Media.objects.filter(can_borrow=True, available=True)

    return render(request, "authentification/espace_client.html", {
        'borrows': borrows,
        'available_media': available_media
    })


@login_required
def staff_dashboard(request):
    # Vérifier si l'utilisateur appartient au groupe staff
    if not request.user.groups.filter(name="staff").exists():
        return redirect("authentification:home")

    # Récupérer tous les emprunts en cours
    borrows = Borrow.objects.filter(is_returned=False)  # Correction du champ utilisé ici

    # Récupérer les emprunts en retard
    overdue_borrows = Borrow.objects.filter(is_returned=False, due_date__lt=timezone.now())

    # Récupérer tous les médias (y compris les jeux de plateau)
    all_media = Media.objects.all()

    return render(request, "authentification/espace_staff.html", {
        'borrows': borrows,  # Correction ici, il faut passer les instances d'emprunt
        'overdue_borrows': overdue_borrows,
        'all_media': all_media
    })
