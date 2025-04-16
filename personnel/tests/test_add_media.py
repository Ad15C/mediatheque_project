import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from personnel.models import Livre, DVD, CD, JeuPlateau, Borrow
from django.test import Client
from personnel.services.borrow_service import borrow_media, return_media
from personnel.exceptions import (
    MediaNotAvailable, MaxBorrowLimitReached,
    MediaAlreadyBorrowed, InvalidReturnOperation, BorrowingError
)


@pytest.fixture
def staff_user():
    user = User.objects.create_user(username='admin', password='admin')
    user.is_staff = True
    user.save()
    return user

@pytest.fixture
def make_authenticated_client():
    def _make(user):
        client = Client()
        client.login(username=user.username, password='admin')  # login avec les bons identifiants
        return client
    return _make

@pytest.mark.django_db
def test_add_media_livre(staff_user, make_authenticated_client):
    client = make_authenticated_client(staff_user)
    url = reverse('add_media')

    data = {
        'name': 'Livre Test',
        'available': True,
        'media_type': 'livre',
        'author': 'Auteur Test',
    }

    response = client.post(url, data)
    assert response.status_code == 302
    assert Livre.objects.count() == 1
    assert Livre.objects.first().name == 'Livre Test'
    assert Livre.objects.first().author == 'Auteur Test'


@pytest.mark.django_db
def test_add_media_dvd(staff_user, make_authenticated_client):
    client = make_authenticated_client(staff_user)
    url = reverse('add_media')

    data = {
        'name': 'DVD Test',
        'available': True,
        'media_type': 'dvd',
        'producer': 'Producteur Test',
    }

    response = client.post(url, data)
    assert response.status_code == 302
    assert DVD.objects.count() == 1
    assert DVD.objects.first().name == 'DVD Test'
    assert DVD.objects.first().producer == 'Producteur Test'


@pytest.mark.django_db
def test_add_media_cd(staff_user, make_authenticated_client):
    client = make_authenticated_client(staff_user)
    url = reverse('add_media')

    data = {
        'name': 'CD Test',
        'available': True,
        'media_type': 'cd',
        'artist': 'Artiste Test',
    }

    response = client.post(url, data)
    assert response.status_code == 302
    assert CD.objects.count() == 1
    assert CD.objects.first().name == 'CD Test'
    assert CD.objects.first().artist == 'Artiste Test'


@pytest.mark.django_db
def test_add_jeu_plateau_without_creators(staff_user, make_authenticated_client):
    client = make_authenticated_client(staff_user)
    url = reverse('add_media')

    # Données de test sans le champ 'creators' pour vérifier la validation
    data = {
        'name': 'Jeu Incomplet',
        'available': True,
        'media_type': 'jeu_plateau',
        'game_type': 'stratégie',  # Absence de 'creators'
    }

    response = client.post(url, data)
    assert response.status_code == 200

    # Vérifier que l'erreur "This field is required." apparaît bien pour 'creators'
    assert b'Ce champ est obligatoire.' in response.content


@pytest.mark.django_db
def test_add_media_invalid_form(staff_user, make_authenticated_client):
    client = make_authenticated_client(staff_user)
    url = reverse('add_media')

    # Cas où 'author' est manquant pour un livre
    data = {
        'name': 'Livre Test',
        'media_type': 'livre',
        'available': True,
    }
    response = client.post(url, data)
    assert response.status_code == 200  # On reste sur la page en cas d'erreur
    assert b'Ce champ est obligatoire.' in response.content


    # Cas où 'artist' est manquant pour un CD
    data = {
        'name': 'CD Test',
        'media_type': 'cd',
        'available': True,
    }
    response = client.post(url, data)
    assert response.status_code == 200
    assert b'Ce champ est obligatoire.' in response.content


    # Cas où 'producer' est manquant pour un DVD
    data = {
        'name': 'DVD Test',
        'media_type': 'dvd',
        'available': True,
    }
    response = client.post(url, data)
    assert response.status_code == 200
    assert b'Ce champ est obligatoire.' in response.content


    # Cas où le type de média est invalide
    data = {
        'name': 'Média Inconnu',
        'media_type': 'vinyle',  # Type non défini
        'available': True,
    }
    response = client.post(url, data)
    assert response.status_code == 200
    decoded_content = response.content.decode('utf-8')  # Décoder en UTF-8
    assert 'Type de média invalide' in decoded_content or 'erreur' in decoded_content


@pytest.mark.django_db
def test_add_cd_without_artist(staff_user, make_authenticated_client):
    client = make_authenticated_client(staff_user)
    url = reverse('add_media')

    data = {
        'name': 'CD Test',
        'available': True,
        'media_type': 'cd',
        'artist': '',
    }

    response = client.post(url, data)
    assert response.status_code == 200  # La page ne doit pas rediriger
    assert b'Ce champ est obligatoire.' in response.content



@pytest.mark.django_db
def test_add_dvd_without_producer(staff_user, make_authenticated_client):
    client = make_authenticated_client(staff_user)
    url = reverse('add_media')

    data = {
        'name': 'DVD Invalide',
        'available': True,
        'media_type': 'dvd',
        'producer' : ''
    }

    response = client.post(url, data)
    assert response.status_code == 200  # La page ne doit pas rediriger
    assert b'Ce champ est obligatoire.' in response.content  # et pas 'This field is required.'


@pytest.mark.django_db
def test_non_staff_cannot_add_media():
    user = User.objects.create_user(username='simple_user', password='test')
    client = Client()
    client.login(username='simple_user', password='test')

    url = reverse('add_media')
    response = client.get(url)
    assert response.status_code in [302, 403]

@pytest.mark.django_db
def test_add_media_valid_form(staff_user, make_authenticated_client):
    client = make_authenticated_client(staff_user)
    url = reverse('add_media')

    data = {
        'name': 'Livre Test',
        'media_type': 'livre',
        'author': 'Auteur Test',
        'available': True,
    }

    response = client.post(url, data)
    # Vérification que la redirection a bien eu lieu après la soumission réussie
    assert response.status_code == 302  # Attendez-vous à une redirection
    assert Livre.objects.count() == 1  # Assurez-vous qu'un livre a été ajouté
    assert Livre.objects.first().name == 'Livre Test'
    assert Livre.objects.first().author == 'Auteur Test'

