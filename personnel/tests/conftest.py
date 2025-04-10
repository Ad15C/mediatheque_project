import pytest
from django.db import connection
from django.contrib.auth.models import User
from personnel.models import Member

# Vider la base de données avant chaque test (optionnel, si vous souhaitez le faire)
@pytest.fixture(autouse=True)
def clear_db():
    cursor = connection.cursor()
    cursor.execute('DELETE FROM personnel_member;')  # Supprimer les membres
    cursor.execute('DELETE FROM auth_user;')         # Supprimer les utilisateurs
    yield

# Créer un utilisateur et un membre unique à chaque test (optionnel)
@pytest.fixture
def create_user_and_member():
    user = User.objects.create(username='testuser', password='password')
    member = Member.objects.create(user=user)
    return user, member
