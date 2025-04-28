import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from mediatheque.staff.models import Media, Borrow
from django.contrib.auth.models import Group
from django.test import TestCase

User = get_user_model()


@pytest.fixture
def create_users_and_media():
    # Créer un utilisateur client
    client_user = User.objects.create_user(
        username='clientuser', password='password123'
    )
    # Créer le groupe 'client' ou obtenir celui existant
    client_group, created = Group.objects.get_or_create(name='client')
    client_user.groups.add(client_group)

    # Créer un utilisateur staff
    staff_user = User.objects.create_user(
        username='staffuser', password='password123'
    )
    # Créer le groupe 'staff' ou obtenir celui existant
    staff_group, created = Group.objects.get_or_create(name='staff')
    staff_user.groups.add(staff_group)

    # Créer des médias
    media1 = Media.objects.create(name='Media 1', available=True, can_borrow=True)
    media2 = Media.objects.create(name='Media 2', available=True, can_borrow=True)

    # Créer un emprunt pour le client
    Borrow.objects.create(user=client_user, media=media1, borrow_date=timezone.now(),
                          due_date=timezone.now() + timezone.timedelta(days=7), is_returned=False)

    return client_user, staff_user, media1, media2


@pytest.mark.django_db
def test_client_dashboard_access(client, create_users_and_media):
    client_user, staff_user, media1, media2 = create_users_and_media

    # Connexion en tant que client
    client.login(username='clientuser', password='password123')

    # Accéder au dashboard du client
    response = client.get(reverse('authentification:espace_client'))

    # Vérifier que la page est bien chargée et que les informations du client sont présentes
    assert response.status_code == 200
    assert "Emprunts en cours" in response.content.decode()
    assert "Media 1" in response.content.decode()  # Le média emprunté par le client

    # Vérifier que le staff ne peut pas accéder au dashboard client
    client.logout()
    client.login(username='staffuser', password='password123')
    response = client.get(reverse('authentification:espace_client'))
    assert response.status_code == 302  # Redirigé vers la page d'accueil (home)
    assert 'location' in response.headers  # Vérification de la redirection


@pytest.mark.django_db
def test_staff_dashboard_access(client, create_users_and_media):
    client_user, staff_user, media1, media2 = create_users_and_media

    # Connexion en tant que staff
    client.login(username='staffuser', password='password123')

    # Accéder au dashboard du staff
    response = client.get(reverse('authentification:espace_staff'))

    # Vérifier que la page est bien chargée et que les informations sont présentes
    assert response.status_code == 200
    assert "Emprunts en retard" in response.content.decode()
    assert "Media 1" in response.content.decode()  # Le média emprunté par un client

    # Vérifier que le client ne peut pas accéder au dashboard staff
    client.logout()
    client.login(username='clientuser', password='password123')
    response = client.get(reverse('authentification:espace_staff'))
    assert response.status_code == 302  # Redirigé vers la page d'accueil (home)
    assert 'location' in response.headers  # Vérification de la redirection


@pytest.mark.django_db
def test_dashboard_no_borrows(client, create_users_and_media):
    client_user, staff_user, media1, media2 = create_users_and_media

    # Créer un client sans emprunts
    no_borrow_user = User.objects.create_user(username='noborrowuser', password='password123')
    no_borrow_user.groups.add(Group.objects.get(name='client'))

    # Connexion en tant que client sans emprunts
    client.login(username='noborrowuser', password='password123')

    # Accéder au dashboard
    response = client.get(reverse('authentification:espace_client'))

    # Vérifier qu'il peut voir un message spécifique si aucun emprunt
    assert response.status_code == 200
    assert "Vous n'avez pas d'emprunts en cours." in response.content.decode()


@pytest.mark.django_db
def test_dashboard_no_media(client, create_users_and_media):
    client_user, staff_user, media1, media2 = create_users_and_media

    # Connexion en tant que staff
    client.login(username='staffuser', password='password123')

    # Accéder au dashboard du staff
    response = client.get(reverse('authentification:espace_staff'))

    # Vérifier que tous les médias sont affichés
    assert response.status_code == 200
    assert 'Media 1' in response.content.decode()
    assert 'Media 2' in response.content.decode()
