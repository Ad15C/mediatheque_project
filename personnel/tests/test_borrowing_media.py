import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from unittest.mock import patch
from personnel.models import Member, Media, Borrow, BorrowingRule
from personnel.messages import GAME_NOT_BORROWABLE, BORROW_BLOCKED, BORROW_TOO_MANY, MEDIA_NOT_AVAILABLE, BORROW_SUCCESS, GAME_NOT_BORROWABLE



@pytest.fixture
def user(db):
    user, created = User.objects.get_or_create(username="testuser", password="password")
    return user

@pytest.fixture
def member(user):
    if not Member.objects.filter(user=user).exists():
        return Member.objects.create(user=user, name="Test User", email="test@example.com")
    return Member.objects.get(user=user)


# Fixtures pour les différents types de médias
@pytest.fixture
def media():
    """Fixture pour créer un livre"""
    return Media.objects.create(name="Livre de test", available=True, media_type="livre")


@pytest.fixture
def cd():
    """Fixture pour créer un CD"""
    return Media.objects.create(name="Test CD", available=True, media_type="CD")


@pytest.fixture
def dvd():
    """Fixture pour créer un DVD"""
    return Media.objects.create(name="Test DVD", available=True, media_type="DVD")


@pytest.fixture
def jeu_plateau():
    """Fixture pour créer un Jeu Plateau non empruntable"""
    return Media.objects.create(name="Test Jeu Plateau", available=True, media_type="jeu_plateau", can_borrow=False)


# Fixture pour la règle d'emprunt
@pytest.fixture
def borrowing_rule():
    """Fixture pour créer une règle d'emprunt"""
    return BorrowingRule.objects.create(active=True, limit=1)


@pytest.mark.django_db
def test_borrow_livre(client, member, media):
    """Test emprunt d'un livre"""
    client.login(username="testuser", password="password")

    response = client.post(reverse('borrowing_media'), {'media_id': media.id})

    # Vérifier que l'emprunt a été créé
    borrow = Borrow.objects.filter(borrower=member, object_id=media.id).exists()
    assert borrow

    # Vérifier que le message de succès est affiché
    messages = list(get_messages(response.wsgi_request))
    assert str(messages[0]) == f"L'emprunt de {media.name} a été effectué avec succès."



@pytest.mark.django_db
def test_borrow_cd(client, member, cd):
    """Test emprunt d'un CD"""
    client.login(username="testuser", password="password")

    response = client.post(reverse('borrowing_media'), {'media_id': cd.id})

    # Vérifier que l'emprunt a été créé
    borrow = Borrow.objects.filter(borrower=member, object_id=cd.id).exists()
    assert borrow

    # Vérifier que le message de succès est affiché
    messages = list(get_messages(response.wsgi_request))
    assert str(messages[0]) == f"L'emprunt de {cd.name} a été effectué avec succès."


@pytest.mark.django_db
def test_borrow_dvd(client, member, dvd):
    """Test emprunt d'un DVD"""
    client.login(username="testuser", password="password")

    response = client.post(reverse('borrowing_media'), {'media_id': dvd.id})

    # Vérifier que l'emprunt a été créé
    borrow = Borrow.objects.filter(borrower=member, object_id=dvd.id).exists()
    assert borrow

    # Vérifier que le message de succès est affiché
    messages = list(get_messages(response.wsgi_request))
    assert str(messages[0]) == f"L'emprunt de {dvd.name} a été effectué avec succès."


@pytest.mark.django_db
def test_borrow_jeu_plateau_not_borrowable(client, member, jeu_plateau):
    """Test que le Jeu Plateau est visible mais non empruntable"""
    client.login(username="testuser", password="password")

    # Tenter d'emprunter un jeu de plateau
    response = client.post(reverse('choose_borrow'), {'media_id': jeu_plateau.id})

    # Vérifier que l'emprunt n'a pas été créé
    borrow = Borrow.objects.filter(borrower=member, object_id=jeu_plateau.id).exists()
    assert not borrow

    # Vérifier que le message indiquant que le jeu ne peut pas être emprunté est affiché
    messages = list(get_messages(response.wsgi_request))
    assert str(messages[0]) == GAME_NOT_BORROWABLE


@pytest.mark.django_db
def test_borrow_media_when_not_logged_in(client):
    """Test que l'utilisateur non connecté ne peut pas emprunter de média"""
    response = client.get(reverse('borrowing_media'))
    assert response.status_code == 302  # Redirigé vers la page de connexion


@pytest.mark.django_db
def test_borrow_media_when_blocked(client, member, media):
    """Test emprunt lorsque le membre est bloqué"""
    member.blocked = True
    member.save()

    client.login(username="testuser", password="password")

    response = client.post(reverse('borrowing_media'), {'media_id': media.id})

    # Vérifier que le message d'erreur est affiché
    messages = list(get_messages(response.wsgi_request))
    assert str(messages[0]) == BORROW_BLOCKED

    # Vérifier qu'aucun emprunt n'est créé
    borrow = Borrow.objects.filter(borrower=member, object_id=media.id).exists()
    assert not borrow


@pytest.mark.django_db
def test_borrow_media_not_available(client, member, media):
    """Test emprunt d'un média non disponible"""
    media.available = False
    media.save()

    client.login(username="testuser", password="password")
    response = client.post(reverse('borrowing_media'), {'media_id': media.id})

    # Vérifier que l'emprunt n'a pas été créé
    borrow = Borrow.objects.filter(borrower=member, object_id=media.id).exists()
    assert not borrow

    # Vérifier que le message d'erreur est affiché
    messages = list(get_messages(response.wsgi_request))
    assert str(messages[0]) == MEDIA_NOT_AVAILABLE


@pytest.mark.django_db
def test_cache_invalidation_on_borrow(client, member, media):
    """Vérifier que le cache est invalidé lors de l'emprunt"""
    with patch('django.core.cache.cache.delete') as mock_cache_delete:
        client.login(username="testuser", password="password")

        # Emprunter un média
        client.post(reverse('borrowing_media'), {'media_id': media.id})

        # Vérifier que cache.delete est appelé
        mock_cache_delete.assert_called_once_with(f"member_{member.id}_borrow_count")


@pytest.mark.django_db
def test_borrow_media_when_limit_reached(client, member, media, dvd, borrowing_rule):
    """Test emprunt lorsque la limite d'emprunts est atteinte"""
    # Créer un emprunt pour respecter la limite
    Borrow.objects.create(borrower=member, content_type=media.content_type, object_id=media.id)

    client.login(username="testuser", password="password")
    response = client.post(reverse('borrowing_media'), {'media_id': dvd.id})

    # Vérifier que le message d'erreur est affiché
    messages = list(get_messages(response.wsgi_request))
    assert str(messages[0]) == BORROW_TOO_MANY

    # Vérifier qu'aucun emprunt n'est créé pour le DVD
    borrow = Borrow.objects.filter(borrower=member, object_id=dvd.id).exists()
    assert not borrow

@pytest.mark.django_db
def test_borrow_multiple_media(client, member, media, cd):
    """Test emprunt de plusieurs médias"""
    client.login(username="testuser", password="password")

    # Emprunter le premier média
    response = client.post(reverse('borrowing_media'), {'media_id': media.id})
    borrow_media = Borrow.objects.filter(borrower=member, object_id=media.id).exists()
    assert borrow_media

    # Emprunter un second média
    response = client.post(reverse('borrowing_media'), {'media_id': cd.id})
    borrow_cd = Borrow.objects.filter(borrower=member, object_id=cd.id).exists()
    assert borrow_cd

    # Vérifier les messages de succès
    messages = list(get_messages(response.wsgi_request))
    assert str(messages[0]) == f"L'emprunt de {media.name} a été effectué avec succès."
    assert str(messages[1]) == f"L'emprunt de {cd.name} a été effectué avec succès."

@pytest.mark.django_db
def test_borrow_media_when_rule_inactive(client, member, media, borrowing_rule):
    """Test emprunt lorsque la règle d'emprunt est inactive"""
    borrowing_rule.active = False
    borrowing_rule.save()

    client.login(username="testuser", password="password")
    response = client.post(reverse('borrowing_media'), {'media_id': media.id})

    # Vérifier que l'emprunt a été créé malgré la règle inactive
    borrow = Borrow.objects.filter(borrower=member, object_id=media.id).exists()
    assert borrow

    # Vérifier que le message de succès est affiché
    messages = list(get_messages(response.wsgi_request))
    assert str(messages[0]) == f"L'emprunt de {media.name} a été effectué avec succès."

@pytest.mark.django_db
def test_borrow_media_when_member_inactive(client, member, media):
    """Test emprunt lorsqu'un membre est inactif"""
    member.is_active = False
    member.save()

    client.login(username="testuser", password="password")
    response = client.post(reverse('borrowing_media'), {'media_id': media.id})

    # Vérifier que l'emprunt n'a pas été créé
    borrow = Borrow.objects.filter(borrower=member, object_id=media.id).exists()
    assert not borrow

    # Vérifier que le message d'erreur est affiché
    messages = list(get_messages(response.wsgi_request))
    assert str(messages[0]) == "Vous ne pouvez pas emprunter un média car votre compte est inactif."
