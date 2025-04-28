import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from django.contrib.auth import get_user_model


# Test d'inscription avec des données valides
@pytest.mark.django_db
def test_signup_view(client):
    response = client.get(reverse('authentification:signup'))
    assert response.status_code == 200
    assert 'authentification/signup.html' in [t.name for t in response.templates]

    # Test de l'inscription avec rôle
    response = client.post(reverse('authentification:signup'), {
        'username': 'newuser',
        'password1': 'P@ssw0rd1234!',  # Utilisez un mot de passe plus sécurisé
        'password2': 'P@ssw0rd1234!',
        'email': 'newuser@example.com',  # L'email doit être sur une ligne distincte
        'role': 'client',  # Assurez-vous que ce champ est bien dans le formulaire
    })

    # Vérification de la redirection après l'inscription
    assert response.status_code == 302  # Vérification que la réponse est une redirection
    assert response.url == reverse('authentification:home')  # Vérification de la redirection vers la page d'accueil

    # Vérification de la création de l'utilisateur
    user_model = get_user_model()
    assert user_model.objects.filter(username='newuser').exists()  # Cette ligne échoue si l'utilisateur n'est pas créé

    # Vérification du message de succès
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert str(messages[0]) == "Inscription réussie ! Vous êtes maintenant connecté."


# Test pour un utilisateur déjà connecté accédant à une page protégée
@pytest.mark.django_db
def test_signup_view_with_login(client):
    # Créer un utilisateur pour se connecter
    user = get_user_model().objects.create_user(
        username='testuser', password='password123', email='testuser@example.com'
    )

    # Se connecter avec cet utilisateur
    client.login(username='testuser', password='password123')

    # Test GET pour la page d'accueil (ou autre page protégée)
    response = client.get(reverse('authentification:home'))
    assert response.status_code == 200  # Page d'accueil accessible après connexion

    # Vérification que l'utilisateur est bien connecté
    assert response.context['user'].is_authenticated  # Vérifie que l'utilisateur est authentifié


# Test pour vérifier que l'inscription échoue avec des mots de passe non correspondants
@pytest.mark.django_db
def test_signup_view_invalid_passwords(client):
    response = client.post(reverse('authentification:signup'), {
        'username': 'newuser',
        'password1': 'password123',
        'password2': 'password124',  # Mots de passe non correspondants
        'email': 'newuser@example.com'
    })

    # Vérifiez que la réponse est bien la page d'inscription
    assert response.status_code == 200
    assert 'authentification/signup.html' in [t.name for t in response.templates]

    # Vérifiez que l'erreur liée aux mots de passe non correspondants est dans le contenu
    assert 'Les mots de passe ne correspondent pas.' in response.content.decode()

    # Vérification des erreurs dans le formulaire
    form = response.context['form']
    assert form.errors  # Vérifiez que des erreurs sont présentes
    assert 'password2' in form.errors  # S'assurer que l'erreur concerne bien le champ "password2"
