import pytest
from django.urls import reverse
from personnel.models import Livre, DVD, CD, JeuPlateau
from django.contrib.auth.models import User


@pytest.fixture
def create_user(db):
    """Fixture pour créer un utilisateur de test."""
    return User.objects.create_user(username='testuser', password='password')


@pytest.fixture
def create_media():
    """Fixture pour créer des objets de type média."""
    livre = Livre.objects.create(name="Livre Test", author="Auteur Test", available=True)
    dvd = DVD.objects.create(name="DVD Test", producer="Producteur Test", available=True)
    cd = CD.objects.create(name="CD Test", artist="Artiste Test", available=True)
    jeu_plateau = JeuPlateau.objects.create(
        name="Jeu Test", creators="Créateur Test", available=False, is_visible=True
    )
    return livre, dvd, cd, jeu_plateau


@pytest.mark.django_db
def test_media_detail_livre(client, create_user, create_media):
    """Test pour le détail d'un livre."""
    livre, _, _, _ = create_media
    client.login(username='testuser', password='password')

    response = client.get(reverse('media_detail', kwargs={'pk': livre.pk}))

    # Vérification du statut et du contenu
    assert response.status_code == 200
    assert "Auteur : Auteur Test" in response.content.decode()
    assert "Disponible : Oui" in response.content.decode()  # "Oui" au lieu de "Disponible"

    # Vérification du lien de retour à la liste des médias
    back_link = reverse('media_list')
    assert f'href="{back_link}"' in response.content.decode()


@pytest.mark.django_db
def test_media_detail_dvd(client, create_user, create_media):
    """Test pour le détail d'un DVD."""
    _, dvd, _, _ = create_media
    client.login(username='testuser', password='password')

    response = client.get(reverse('media_detail', kwargs={'pk': dvd.pk}))

    # Vérification du statut et du contenu
    assert response.status_code == 200
    assert "Producteur : Producteur Test" in response.content.decode()
    assert "Disponible : Oui" in response.content.decode()


@pytest.mark.django_db
def test_media_detail_cd(client, create_user, create_media):
    """Test pour le détail d'un CD."""
    _, _, cd, _ = create_media
    client.login(username='testuser', password='password')

    response = client.get(reverse('media_detail', kwargs={'pk': cd.pk}))

    # Vérification du statut et du contenu
    assert response.status_code == 200
    assert "Artiste : Artiste Test" in response.content.decode()
    assert "Disponible : Oui" in response.content.decode()


@pytest.mark.django_db
def test_media_detail_jeu_plateau(client):
    """Test pour le détail d'un jeu de plateau."""
    user = User.objects.create_user(username='testuser', password='password')

    # Créer un objet JeuPlateau
    jeu_plateau = JeuPlateau.objects.create(
        name="Jeu Test",
        creators="Créateur Test",
        is_visible=True,  # Le média est visible
        available=False   # Le jeu n'est pas disponible
    )

    # Simuler la connexion de l'utilisateur
    client.login(username='testuser', password='password')

    # Effectuer la requête GET pour obtenir la page de détail du jeu de plateau
    response = client.get(reverse('media_detail', kwargs={'pk': jeu_plateau.pk}))

    # Vérification du statut HTTP
    assert response.status_code == 200

    # Vérification de l'affichage des informations du jeu de plateau
    assert "Créateurs : Créateur Test" in response.content.decode()
    assert "Disponible : Non" in response.content.decode()

    # Vérifier le lien de retour à la liste des médias
    back_link = reverse('media_list')
    assert f'href="{back_link}"' in response.content.decode()



