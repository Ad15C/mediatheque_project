import pytest
import uuid
from personnel.models import Borrow, Member
from django.urls import reverse
from django.contrib.auth.models import User

# ========== FIXTURES ==========

@pytest.fixture
def test_user(db):
    """Créer un utilisateur non-staff."""
    return User.objects.create_user(username='testuser', password='testpassword')

@pytest.fixture
def test_staff_user(db):
    """Créer un utilisateur staff."""
    return User.objects.create_user(username='staffuser', password='staffpassword', is_staff=True)

@pytest.fixture
def logged_in_client(client, test_user):
    """Connecte un client avec un utilisateur non-staff."""
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
    if not Member.objects.filter(user=user).exists():
        member = Member.objects.create(user=user)
    else:
        member = Member.objects.get(user=user)

    return user, member


# ========== TESTS ==========

@pytest.mark.django_db
def test_index_for_authenticated_user(logged_in_client):
    """Test que la page d'accueil est accessible pour un utilisateur authentifié."""
    response = logged_in_client.get(reverse('index'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_index_for_authenticated_user_with_content(logged_in_staff_client, create_user_and_member):
    """Test que la page d'accueil affiche correctement les emprunts et membres pour un utilisateur authentifié."""
    user, member = create_user_and_member  # Crée un utilisateur et un membre unique pour ce test

    response = logged_in_staff_client.get(reverse('index'))

    # Vérifie que le nombre d'emprunts et de membres correspond
    borrow_count = Borrow.objects.count()
    member_count = Member.objects.count()

    # Assure-toi que la réponse est correcte
    assert response.status_code == 200
    assert borrow_count == len(response.context['borrows'])
    assert member_count == len(response.context['members'])

    # Vérifie le contenu de la page pour s'assurer que les éléments sont bien présents
    content = response.content.decode()
    assert "Liste des médias" in content
    assert "Emprunter un média" in content
    assert "Retourner un média" in content
    assert "Ajouter un média" in content
    assert "Liste des membres" in content
    assert "Ajouter un membre" in content
    assert "Membres en retard" in content
    assert "Accueil" in content


@pytest.mark.django_db
def test_permission_denied_for_non_staff_user(logged_in_client):
    """Test que les utilisateurs non-staff sont redirigés correctement lorsqu'ils tentent d'accéder à des pages restreintes."""
    response = logged_in_client.get(reverse('media_list'))
    assert response.status_code == 302
    assert response.url.startswith('/personnel/no-permission/')


@pytest.mark.django_db
def test_index_for_staff_user(logged_in_staff_client):
    """Test que la page d'accueil est accessible pour un utilisateur staff."""
    response = logged_in_staff_client.get(reverse('index'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_index_shows_borrows_and_members(logged_in_staff_client, create_user_and_member):
    """Test que les emprunts et les membres sont affichés correctement sur la page d'accueil."""
    # Crée un utilisateur et un membre unique pour ce test
    user, member = create_user_and_member

    response = logged_in_staff_client.get(reverse('index'))

    # Vérifie si le nombre de membres et d'emprunts est bien affiché sur la page
    assert str(Member.objects.count()) in response.content.decode()
    assert str(Borrow.objects.count()) in response.content.decode()
