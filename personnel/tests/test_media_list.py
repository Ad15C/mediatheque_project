import pytest
from django.urls import reverse
from personnel.models import Livre, DVD, CD, JeuPlateau


@pytest.mark.django_db
class TestMediaListView:

    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.client = client
        self.url = reverse("media_list")

    def test_media_list_empty(self):
        """La page s'affiche même s'il n'y a aucun média."""
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert "Aucun livre disponible." in response.content.decode()
        assert "Aucun DVD disponible." in response.content.decode()
        assert "Aucun CD disponible." in response.content.decode()
        assert "Aucun jeu de plateau disponible." in response.content.decode()

    def test_display_all_media(self):
        """Tous les types de médias s'affichent."""
        Livre.objects.create(name="Le Petit Prince", author="Saint-Exupéry", available=True)
        DVD.objects.create(name="Inception", producer="Nolan", available=True)
        CD.objects.create(name="Thriller", artist="Michael Jackson", available=True)
        JeuPlateau.objects.create(name="Catan", creators="Klaus Teuber")
        response = self.client.get(self.url)
        content = response.content.decode()
        assert "Le Petit Prince" in content
        assert "Inception" in content
        assert "Thriller" in content
        assert "Catan" in content

    def test_display_unavailable_media(self):
        """Médias indisponibles affichent '(indisponible)'."""
        Livre.objects.create(name="Unavailable Book", author="Auteur", available=False)
        DVD.objects.create(name="Unavailable DVD", producer="Réalisateur", available=False)
        CD.objects.create(name="Unavailable CD", artist="Artiste", available=False)
        response = self.client.get(self.url)
        assert response.content.decode().count("(indisponible)") == 3

    def test_media_detail_links_present(self):
        """Chaque média a un lien vers sa page de détail."""
        livre = Livre.objects.create(name="1984", author="Orwell", available=True)
        dvd = DVD.objects.create(name="Matrix", producer="Wachowski", available=True)
        response = self.client.get(self.url)
        assert reverse("media_detail", args=[livre.pk]) in response.content.decode()
        assert reverse("media_detail", args=[dvd.pk]) in response.content.decode()

    def test_special_characters_displayed(self):
        """Les caractères spéciaux sont bien affichés."""
        Livre.objects.create(name="L'Étranger !@#", author="Camus", available=True)
        response = self.client.get(self.url)
        content = response.content.decode().strip()

        # Affiche le contenu pour déboguer
        print(content)  # Pour voir ce qui est réellement dans le contenu HTML

        # Cherche l'entité HTML pour l'apostrophe (&#x27;)
        assert "L&#x27;Étranger !@#" in content  # Cherche l'entité HTML pour l'apostrophe

    def test_very_long_media_name_displayed(self):
        """Les noms très longs ne cassent pas la page."""
        long_name = "A" * 300
        DVD.objects.create(name=long_name, producer="Quelqu’un", available=True)
        response = self.client.get(self.url)
        assert long_name in response.content.decode()

    def test_page_accessible_without_login(self):
        """La page doit être accessible sans authentification (si non protégée)."""
        response = self.client.get(self.url)
        assert response.status_code == 200

    def test_authenticated_user_ui_elements(self, django_user_model):
        """Un utilisateur connecté voit les éléments liés à la déconnexion."""
        user = django_user_model.objects.create_user(username="testuser", password="pass123")
        self.client.login(username="testuser", password="pass123")
        response = self.client.get(self.url)
        assert "Se déconnecter" in response.content.decode()
