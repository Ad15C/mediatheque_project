from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class IndexPageTest(TestCase):
    def setUp(self):
        # Créer un utilisateur pour tester les fonctionnalités authentifiées
        self.user = User.objects.create_user(username='testuser', password='testpassword')

    def test_index_page_status_code(self):
        """
        Tester que la page d'index renvoie un code de statut 200
        """
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_index_page_title(self):
        """
        Tester que le titre de la page d'index est bien défini.
        """
        response = self.client.get(reverse('index'))
        self.assertContains(response, '<title>Accueil</title>')

    def test_index_page_content(self):
        """
        Tester que le contenu spécifique est bien présent dans la page d'accueil.
        """
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Bienvenue sur le site de la Médiathèque')  # Pas besoin de la balise <h1>, juste le texte

    def test_authenticated_user_links(self):
        """
        Tester les liens visibles pour un utilisateur authentifié.
        """
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Se déconnecter')
        self.assertContains(response, 'Liste des médias')

    def test_guest_user_links(self):
        """
        Tester les liens visibles pour un utilisateur non authentifié.
        """
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Se connecter')
        self.assertContains(response, 'Liste des médias')

    def test_navigation_links(self):
        """
        Tester que les liens de navigation sont présents sur la page.
        """
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Liste des médias')
        self.assertContains(response, 'Emprunter un média')
        self.assertContains(response, 'Retourner un média')
        self.assertContains(response, 'Ajouter un média')
        self.assertContains(response, 'Liste des membres')
        self.assertContains(response, 'Ajouter un membre')
        self.assertContains(response, 'Retour à l\'accueil')
