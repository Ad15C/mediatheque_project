import pytest
import uuid
from django.db import connection
from django.contrib.auth.models import User
from personnel.models import Member
from django.db import transaction

@pytest.fixture(autouse=True)
def clear_db():
    """Effacer les enregistrements dans la base de données avant chaque test."""
    # Supprimer les membres et les utilisateurs avant chaque test
    Member.objects.all().delete()
    User.objects.all().delete()
    yield

@pytest.fixture(autouse=True)
def cleanup_after_tests():
    """Nettoyage automatique après chaque test, avec gestion des transactions"""
    with transaction.atomic():
        yield
        # Supprimer tous les membres et utilisateurs après chaque test
        Member.objects.all().delete()
        User.objects.all().delete()


# Créer un utilisateur unique et un membre associé à chaque test
@pytest.fixture
def create_user_and_member():
    # Utilisation d'un uuid pour garantir l'unicité
    unique_username = f"user_{uuid.uuid4().hex[:8]}"  # Crée un nom d'utilisateur unique
    user = User.objects.create(username=unique_username, password='password')
    member = Member.objects.create(user=user)
    return user, member
