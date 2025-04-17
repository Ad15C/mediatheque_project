import pytest
from django.urls import reverse
from personnel.models import Livre, DVD, CD, JeuPlateau


@pytest.mark.django_db
class TestMediaListView:
    @pytest.fixture(autouse=True)
    def setup(self, client, django_user_model):
        self.client = client
        self.user = django_user_model.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.client.login(username="staff", password="pass")
        self.url = reverse("media_list")

    def test_media_list_page_accessible(self):
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert "Liste des médias" in response.content.decode()

    def test_media_list_empty(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        assert "Aucun livre disponible." in content
        assert "Aucun DVD disponible." in content
        assert "Aucun CD disponible." in content
        assert "Aucun jeu de plateau disponible." in content

    def test_display_all_media(self):
        Livre.objects.create(name="Le Petit Prince", author="Saint-Exupéry")
        DVD.objects.create(name="Inception", producer="Nolan")
        CD.objects.create(name="Thriller", artist="Michael Jackson")
        JeuPlateau.objects.create(name="Catan", creators="Teuber")
        response = self.client.get(self.url)
        content = response.content.decode()
        assert "Le Petit Prince" in content
        assert "Inception" in content
        assert "Thriller" in content
        assert "Catan" in content

    def test_display_unavailable_media(self):
        Livre.objects.create(name="Unavailable Book", author="Auteur", available=False)
        DVD.objects.create(name="Unavailable DVD", producer="Réalisateur", available=False)
        CD.objects.create(name="Unavailable CD", artist="Artiste", available=False)
        response = self.client.get(self.url)
        assert response.content.decode().count("(indisponible)") == 3

    def test_media_detail_links_present(self):
        livre = Livre.objects.create(name="1984", author="Orwell")
        dvd = DVD.objects.create(name="Matrix", producer="Wachowski")
        response = self.client.get(self.url)
        content = response.content.decode()
        assert reverse("media_detail", args=[livre.pk]) in content
        assert reverse("media_detail", args=[dvd.pk]) in content

    def test_special_characters_displayed(self):
        Livre.objects.create(name="L'Étranger !@#", author="Camus")
        response = self.client.get(self.url)
        content = response.content.decode()
        assert "L&#x27;Étranger !@#" in content

    def test_very_long_media_name_displayed(self):
        long_name = "A" * 300
        DVD.objects.create(name=long_name, producer="Réalisateur")
        response = self.client.get(self.url)
        assert long_name in response.content.decode()

    def test_media_ordering_by_name(self):
        Livre.objects.create(name="Z Livre", author="Z")
        Livre.objects.create(name="A Livre", author="A")
        response = self.client.get(self.url)
        content = response.content.decode()
        assert content.index("A Livre") < content.index("Z Livre")

    def test_add_media_button_visible_for_staff(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        assert reverse("add_media") in content
        assert "Ajouter un média" in response.content.decode()



@pytest.mark.django_db
def test_media_list_redirects_if_not_logged_in(client):
    response = client.get(reverse("media_list"))
    assert response.status_code == 302
    assert "/login/" in response.url


@pytest.mark.django_db
def test_media_list_access_denied_for_non_staff(client, django_user_model):
    user = django_user_model.objects.create_user(username="user", password="pass")
    client.login(username="user", password="pass")
    response = client.get(reverse("media_list"))
    assert response.status_code == 302
    assert "no-permission" in response.url


@pytest.mark.django_db
def test_add_media_button_hidden_for_non_staff(client, django_user_model):
    user = django_user_model.objects.create_user(username="user", password="pass")
    client.login(username="user", password="pass")
    response = client.get(reverse("media_list"))
    assert "Ajouter un média" not in response.content.decode()


@pytest.mark.django_db
def test_add_media_page_accessible_for_staff(client, django_user_model):
    user = django_user_model.objects.create_user(username="admin", password="pass", is_staff=True)
    client.login(username="admin", password="pass")
    response = client.get(reverse("add_media"))
    assert response.status_code == 200
    assert '<a href="' + reverse('add_media') + '"' in response.content.decode()

