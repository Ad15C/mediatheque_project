import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from personnel.models import Livre, DVD, CD, JeuPlateau
from django.test import Client

@pytest.fixture
def user():
    # Crée un utilisateur pour les tests
    return User.objects.create_user(username='testuser', password='password')

@pytest.fixture
def client(user):
    # Crée un client de test pour simuler des requêtes HTTP
    client = Client()
    client.login(username='testuser', password='password')
    return client

@pytest.mark.django_db  # Marque le test pour permettre l'accès à la base de données
def test_add_media_livre(client):
    # Test pour l'ajout d'un livre
    url = reverse('add_media')  # Remplacez par le nom de votre URL pour ajouter un média

    data = {
        'name': 'Livre Test',
        'available': True,
        'media_type': 'livre',
        'author': 'Auteur Test',
    }

    response = client.post(url, data)

    # Vérifiez que la réponse est une redirection après avoir soumis le formulaire
    assert response.status_code == 302  # La redirection doit avoir un code 302
    assert Livre.objects.count() == 1  # Assurez-vous qu'un objet Livre a été créé
    assert Livre.objects.first().name == 'Livre Test'
    assert Livre.objects.first().author == 'Auteur Test'

@pytest.mark.django_db  # Marque le test pour permettre l'accès à la base de données
def test_add_media_dvd(client):
    # Test pour l'ajout d'un DVD
    url = reverse('add_media')  # Remplacez par le nom de votre URL pour ajouter un média

    data = {
        'name': 'DVD Test',
        'available': True,
        'media_type': 'dvd',
        'producer': 'Producteur Test',
    }

    response = client.post(url, data)

    # Vérifiez que la réponse est une redirection après avoir soumis le formulaire
    assert response.status_code == 302  # La redirection doit avoir un code 302
    assert DVD.objects.count() == 1  # Assurez-vous qu'un objet DVD a été créé
    assert DVD.objects.first().name == 'DVD Test'
    assert DVD.objects.first().producer == 'Producteur Test'

@pytest.mark.django_db  # Marque le test pour permettre l'accès à la base de données
def test_add_media_cd(client):
    # Test pour l'ajout d'un CD
    url = reverse('add_media')  # Remplacez par le nom de votre URL pour ajouter un média

    data = {
        'name': 'CD Test',
        'available': True,
        'media_type': 'cd',
        'artist': 'Artiste Test',
    }

    response = client.post(url, data)

    # Vérifiez que la réponse est une redirection après avoir soumis le formulaire
    assert response.status_code == 302  # La redirection doit avoir un code 302
    assert CD.objects.count() == 1  # Assurez-vous qu'un objet CD a été créé
    assert CD.objects.first().name == 'CD Test'
    assert CD.objects.first().artist == 'Artiste Test'

@pytest.mark.django_db  # Marque le test pour permettre l'accès à la base de données
def test_add_media_jeu_plateau(client):
    # Test pour l'ajout d'un jeu de plateau
    url = reverse('add_media')


    data = {
        'name': 'Jeu Plateau Test',
        'available': True,
        'media_type': 'jeu_plateau',
        'creators': 'Créateur Test',
    }

    response = client.post(url, data)

    # Vérifiez que la réponse est une redirection après avoir soumis le formulaire
    assert response.status_code == 302  # La redirection doit avoir un code 302
    assert JeuPlateau.objects.count() == 1  # Assurez-vous qu'un objet JeuPlateau a été créé
    assert JeuPlateau.objects.first().name == 'Jeu Plateau Test'
    assert JeuPlateau.objects.first().creators == 'Créateur Test'


@pytest.mark.django_db
def test_add_media_invalid_form(client):
    # Simuler l'envoi d'un formulaire sans l'auteur pour un livre
    response = client.post(reverse('add_media'), {
        'name': 'Mon Livre',
        'media_type': 'livre',  # Type de média livre
        'available': True,  # Autre champ valide
    })

    # Vérifier que l'erreur spécifique au champ 'author' est présente
    assert b'This field is required.' in response.content

    # Vérifier que l'erreur globale (non field) pour l'auteur est présente avec l'apostrophe encodée
    assert b"L&#x27;auteur est requis pour un livre." in response.content