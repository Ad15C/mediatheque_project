import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client


@pytest.fixture
def user(db):
    """Création d'un utilisateur de test"""
    User = get_user_model()
    user = User.objects.create_user(username='testuser', password='testpassword')
    return user


@pytest.fixture
def client():
    """Fixture pour le client de test"""
    return Client()


def test_logout_view(client, user):
    """Test de la vue de déconnexion"""

    # Connecter l'utilisateur avant de tester la déconnexion
    client.login(username='testuser', password='testpassword')

    # Vérifier que l'utilisateur est connecté
    response = client.get(reverse('authentification:login'))  # Ou toute page nécessitant d'être connecté
    assert response.status_code == 200

    # Aller à la vue de déconnexion
    response = client.get(reverse('authentification:logout'))

    # Vérifier la redirection vers la page de connexion
    assert response.status_code == 302
    assert response.url == reverse('authentification:login')

    # Vérifier que l'utilisateur est déconnecté (il ne devrait plus être authentifié)
    response = client.get(reverse('authentification:login'))
    assert response.status_code == 200

    # Vérifier que le message de succès est affiché
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].message == "Vous êtes maintenant déconnecté."

    # Vérifier que l'utilisateur est déconnecté
    assert not client.session.get('_auth_user_id')  # L'utilisateur ne doit plus être authentifié
