import os
import django
import pytest
from django.contrib.auth import get_user_model


# Assure-toi que Django est configuré avant tout
os.environ['DJANGO_SETTINGS_MODULE'] = 'mediatheque.settings'
django.setup()


@pytest.fixture(scope='session')
def setup_django():
    pass


@pytest.fixture
def user():
    # Créer un utilisateur test pour tes tests
    user = get_user_model().objects.create_user(username='testuser', password='12345')
    return user
