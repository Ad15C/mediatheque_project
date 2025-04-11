from django.test import TestCase
from django.urls import reverse
from personnel.models import Livre, DVD, CD, JeuPlateau
from django.contrib.auth.models import User

class MediaDetailViewTests(TestCase):

    def setUp(self):
        # Créer un utilisateur pour les tests authentifiés
        self.user = User.objects.create_user(username='testuser', password='password')

        # Créer des instances des différents types de médias
        self.livre = Livre.objects.create(name="Livre Test", author="Auteur Test", available=True)
        self.dvd = DVD.objects.create(name="DVD Test", producer="Producteur Test", available=True)
        self.cd = CD.objects.create(name="CD Test", artist="Artiste Test", available=True)
        self.jeu_plateau = JeuPlateau.objects.create(
            name="Jeu Test", creators="Créateur Test", available=False, is_visible=True
        )

    def test_media_detail_livre(self):
        # Créer un livre disponible (on peut l'emprunter)
        self.livre = Livre.objects.create(
            name="Livre Test", author="Auteur Test", available=True
        )

        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('media_detail', kwargs={'pk': self.livre.pk}))

        # Afficher le contenu de la réponse pour déboguer
        print(response.content.decode())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auteur : Auteur Test")
        self.assertContains(response, "Disponible : Oui")  # Modifié pour "Oui"

        # Vérifier que le lien de retour à la liste des médias fonctionne
        back_link = reverse('media_list')
        self.assertContains(response, f'href="{back_link}"')  # Vérifie que le lien pointe vers la liste des médias

    def test_media_detail_dvd(self):
        # Test pour le détail d'un DVD
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('media_detail', kwargs={'pk': self.dvd.pk}))

        # Vérification du code de statut et du contenu
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Producteur : Producteur Test")
        self.assertContains(response, "Disponible : Oui")

    def test_media_detail_cd(self):
        # Test pour le détail d'un CD
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('media_detail', kwargs={'pk': self.cd.pk}))

        # Vérification du code de statut et du contenu
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Artiste : Artiste Test")
        self.assertContains(response, "Disponible : Oui")

    def test_media_detail_jeu_plateau(self):
        User.objects.filter(username='testuser').delete()

        user = User.objects.create_user(username='testuser', password='password')

        jeu_plateau = JeuPlateau.objects.create(
            name="Jeu Test",
            creators="Créateur Test",
            is_visible=True,  # Le média est visible
            available=False   # Le jeu n'est pas disponible
        )

        self.client.login(username='testuser', password='password')

        response = self.client.get(reverse('media_detail', args=[jeu_plateau.pk]))