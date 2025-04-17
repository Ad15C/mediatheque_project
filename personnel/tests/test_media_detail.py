import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from personnel.models import Livre, DVD, CD, JeuPlateau, Borrow, Member
import uuid
from urllib.parse import urlparse
from personnel.views import MediaCreateView, MemberCreateView

# FIXTURES

@pytest.fixture
def non_staff_user(db):
    """Créer un utilisateur non-staff générique."""
    return User.objects.create_user(username='testuser', password='testpassword')


@pytest.fixture
def test_staff_user(db):
    """Créer un utilisateur staff."""
    return User.objects.create_user(username='staffuser', password='staffpassword', is_staff=True)

@pytest.fixture
def logged_in_client(client, non_staff_user):
    client.login(username='testuser', password='testpassword')
    return client


@pytest.fixture
def logged_in_staff_client(client, test_staff_user):
    """Connecte un client avec un utilisateur staff."""
    client.login(username='staffuser', password='staffpassword')
    return client

@pytest.fixture
def create_user_and_member(db):
    """Créer un utilisateur unique et un membre associé."""
    unique_username = f"user_{uuid.uuid4().hex[:8]}"  # Crée un username unique pour chaque test
    user = User.objects.create_user(username=unique_username, password='password')

    # Vérifie si un membre existe déjà pour cet utilisateur, sinon crée un nouveau membre
    member, created = Member.objects.get_or_create(user=user)

    return user, member

@pytest.fixture
def livre(db):
    return Livre.objects.create(name='La Femme de Ménage', author='Freida McFadden')

@pytest.fixture
def dvd(db):
    return DVD.objects.create(name='Game of Thrones', producer='George R. R. Martin')

@pytest.fixture
def cd(db):
    return CD.objects.create(name='25', artist='Adele')

@pytest.fixture
def jeu_plateau(db):
    return JeuPlateau.objects.create(name="Monopoly", creators="Charles Darrow")



@pytest.fixture
def member_for_staff_user(db, staff_user):
    return Member.objects.create(user=staff_user)

#  TESTS LISTE -
@pytest.mark.django_db
def test_media_list_display(client, staff_user, livre, dvd, cd, jeu_plateau):
    client.login(username='staffuser', password='staffpassword')
    url = reverse('media_list')
    response = client.get(url)

    # Vérifie que la réponse est valide
    assert response.status_code == 200

    content = response.content.decode()

    # Vérifie la présence des médias dans la réponse
    assert "La Femme de Ménage" in content
    assert "Game of Thrones" in content
    assert "25" in content
    assert "Monopoly" in content
    assert "Freida McFadden" in content
    assert "George R. R. Martin" in content
    assert "Adele" in content
    assert "Charles Darrow" in content
    assert 'Détails' in content
    assert 'Emprunter' in content


@pytest.mark.django_db
def test_media_detail_link(client, staff_user, livre):
    client.login(username='staffuser', password='staffpassword')
    url = reverse('media_detail', args=[livre.pk])
    response = client.get(url)

    # Vérifie que la réponse est valide
    assert response.status_code == 200
    assert "La Femme de Ménage" in response.content.decode()


@pytest.mark.django_db
def test_no_borrow_button_if_not_available(client, staff_user, livre):
    livre.available = False
    livre.save()
    client.login(username='staffuser', password='staffpassword')
    url = reverse('media_list')
    response = client.get(url)
    assert 'Emprunter' not in response.content.decode()
    assert 'Non disponible' in response.content.decode()



#  TESTS PERMISSIONS

@pytest.mark.django_db
def test_media_list_redirect_for_non_authenticated_user(client):
    """Test que les utilisateurs non-authentifiés sont redirigés vers la page de login lorsqu'ils essaient d'accéder à la liste des médias."""
    url = reverse('media_list')
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith('/login/')



@pytest.mark.django_db
def test_media_list_redirect_for_non_staff_user(client, non_staff_user):
    """Test que les utilisateurs non-staff sont redirigés vers la page de login lorsqu'ils essaient d'accéder à la liste des médias."""
    client.login(username='testuser', password='testpassword')
    response = client.get(reverse('media_list'))
    assert response.status_code == 302
    assert response.url.startswith('/login/')



@pytest.mark.django_db
def test_media_detail_redirect_for_non_staff_user(client, non_staff_user, livre):
    client.login(username='testuser', password='testpassword')
    url = reverse('media_detail', args=[livre.pk])
    response = client.get(url)

    assert response.status_code == 302

    # Compare uniquement le chemin (sans ?next=...)
    assert urlparse(response.url).path == reverse('no_permission')






