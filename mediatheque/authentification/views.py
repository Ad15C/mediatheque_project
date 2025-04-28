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
            user = form.save()
            login(request, user)
            messages.success(request, "Inscription réussie ! Vous êtes maintenant connecté.")
            return redirect('home')  # Redirection après inscription réussie
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
                    return redirect('staff_dashboard')  # Rediriger vers le tableau de bord staff
                else:
                    return redirect('client_dashboard')  # Rediriger vers le tableau de bord client
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
    return redirect('login')


# Décorateur pour vérifier que l'utilisateur est connecté
@login_required
def client_dashboard(request):
    if not request.user.groups.filter(name='client').exists():
        return redirect("home")

    borrows = Borrow.objects.filter(user=request.user, is_returned=False)
    available_media = Media.objects.filter(can_borrow=True, available=True)

    return render(request, "authentification/client_dashboard.html", {
        'borrows': borrows,
        'available_media': available_media
    })



@login_required
def staff_dashboard(request):
    # Vérifier si l'utilisateur appartient au groupe staff
    if not request.user.groups.filter(name="staff").exists():
        return redirect("home")

    # Récupérer tous les emprunts en cours
    borrows = Borrow.objects.filter(is_returned=False)  # Correction du champ utilisé ici

    # Récupérer les emprunts en retard
    overdue_borrows = Borrow.objects.filter(is_returned=False, due_date__lt=timezone.now())

    # Récupérer tous les médias (y compris les jeux de plateau)
    all_media = Media.objects.all()

    return render(request, "authentification/staff_dashboard.html", {
        'borrows': borrows,  # Correction ici, il faut passer les instances d'emprunt
        'overdue_borrows': overdue_borrows,
        'all_media': all_media
    })
