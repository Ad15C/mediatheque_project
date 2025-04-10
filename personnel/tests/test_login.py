from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model  # Correct import

class LoginViewTest(TestCase):

    def setUp(self):
        # Utiliser get_user_model pour obtenir le modèle d'utilisateur
        user_model = get_user_model()  # Renommé en minuscule
        self.user = user_model.objects.create_user(username='testuser', password='testpassword')

    def test_login_view_with_valid_credentials(self):
        # Tester la connexion avec des informations valides
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'testpassword'})

        # Vérifier que la réponse est une redirection (code 302)
        self.assertEqual(response.status_code, 302)

        # Suivre la redirection vers la page d'accueil
        response = self.client.get(response.url)

        # Vérifier que l'utilisateur est authentifié
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        # Vérifier si l'utilisateur est redirigé vers la page d'accueil
        # Cela peut se produire si la page d'accueil utilise @login_required
        if response.status_code == 302:
            # Si une redirection a encore lieu, il peut s'agir d'une redirection vers la page d'accueil
            response = self.client.get(reverse('index'))

        # Vérifier que la page d'accueil est accessible et renvoie un code 200
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'personnel/index.html')


    def test_login_view_with_invalid_credentials(self):
        # Tester la connexion avec des informations invalides
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'wrongpassword'})

        # Vérifier si le message d'erreur apparaît dans la réponse (en français)
        self.assertContains(response, "Nom d’utilisateur ou mot de passe incorrect.")

    def test_login_view_get_request(self):
        # Tester l'accès à la page de connexion via une requête GET
        response = self.client.get(reverse('login'))

        # Vérifier que la page de connexion se charge correctement (code 200)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_authenticated_user_redirect_to_index(self):
        # Se connecter manuellement
        self.client.login(username='testuser', password='testpassword')

        # Vérifier que la page d'index est accessible
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)  # La page d'index doit répondre avec un code 200
