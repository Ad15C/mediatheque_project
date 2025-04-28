from bs4 import BeautifulSoup
from authentification.forms import CustomUserCreationForm
import pytest
from django.contrib.auth.models import Group
from django.urls import reverse


@pytest.mark.django_db
def test_login_view(client, django_user_model):
    # Création d’un utilisateur
    user = django_user_model.objects.create_user(username='testuser', password='12345')

    # Créer le groupe 'client' si il n'existe pas
    client_group, created = Group.objects.get_or_create(name='client')

    # Assigner l'utilisateur au groupe 'client'
    user.groups.add(client_group)

    # Authentifier l'utilisateur dans le test
    client.login(username='testuser', password='12345')

    # 1. Accéder à la page de login
    response = client.get(reverse('authentification:login'))
    assert response.status_code == 200
    assert 'authentification/login.html' in [t.name for t in response.templates]

    # 2. Connexion avec de mauvaises informations
    response = client.post(reverse('authentification:login'), {'username': 'testuser', 'password': 'wrongpassword'})
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.get_text()
    assert "Nom d'utilisateur ou mot de passe incorrect" in text

    # 3. Connexion avec les bonnes informations
    response = client.post(reverse('authentification:login'), {'username': 'testuser', 'password': '12345'})
    assert response.status_code == 302
    assert response.url == reverse('authentification:espace_client')
