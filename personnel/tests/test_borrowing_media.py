from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.contrib.contenttypes.models import ContentType
from personnel.models import Member, Media, Borrow, BorrowingRule
from personnel.messages import BORROW_BLOCKED, BORROW_TOO_MANY, MEDIA_NOT_AVAILABLE, DELAYED_BORROW
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest

# Fonctions de validation des critères d'emprunt
def is_blocked(member):
    return member.blocked

def has_delayed_borrow(member):
    return member.got_delayed()

def is_media_available(media):
    return media.available

def has_reached_borrow_limit(member):
    limite = BorrowingRule.get_active_limit()
    return member.currently_borrowed() >= limite

def check_borrow_criteria(member, selected_media):
    if is_blocked(member):
        return False, BORROW_BLOCKED

    if has_delayed_borrow(member):
        return False, DELAYED_BORROW

    if not is_media_available(selected_media):
        return False, MEDIA_NOT_AVAILABLE

    if has_reached_borrow_limit(member):
        return False, BORROW_TOO_MANY

    return True, None


class BorrowingMediaTestCase(TestCase):

    def setUp(self):
        """Prépare les données pour les tests"""
        self.user, created = User.objects.get_or_create(username="testuser", defaults={'password': 'password'})
        self.member, created = Member.objects.get_or_create(user=self.user, defaults={'blocked': False})
        self.livre = Media.objects.create(name="Livre de test", available=True, media_type="livre")
        self.dvd = Media.objects.create(name="DVD de test", available=True, media_type="dvd")
        self.cd = Media.objects.create(name="Test CD", available=True, media_type="cd")
        self.jeuplateau = Media.objects.create(name="Test Jeu de Plateau", available=True, media_type="Jeu de Plateau")

    def login_user(self):
        """Connexion de l'utilisateur pour les tests"""
        self.client.login(username="testuser", password="password")

    def tearDown(self):
        """Supprime les données après chaque test"""
        Borrow.objects.all().delete()
        Member.objects.all().delete()
        Media.objects.all().delete()
        User.objects.all().delete()

    def test_borrow_valid_media(self):
        """Test emprunt d'un média valide"""
        self.login_user()
        response = self.client.post(reverse('borrowing_media'), {'media_id': self.livre.id})

        # Vérifier que l'emprunt a été créé
        borrow = Borrow.objects.filter(borrower=self.member, object_id=self.livre.id).exists()
        self.assertTrue(borrow)

        # Vérifier que le message de succès est affiché
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), f"L'emprunt de {self.livre.name} a été effectué avec succès.")

    def test_borrowing_media_when_not_logged_in(self):
        """Test que l'utilisateur non connecté ne peut pas emprunter de média"""
        response = self.client.get(reverse('borrowing_media'))
        self.assertRedirects(response, '/login/')

    def test_borrow_media_when_blocked(self):
        """Test emprunt lorsque le membre est bloqué"""
        self.member.blocked = True
        self.member.save()
        self.login_user()

        response = self.client.post(reverse('borrowing_media'), {'media_id': self.livre.id})

        # Vérifier que le message d'erreur est affiché
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), BORROW_BLOCKED)

        # Vérifier qu'aucun emprunt n'est créé
        borrow = Borrow.objects.filter(borrower=self.member, object_id=self.livre.id).exists()
        self.assertFalse(borrow)

    def test_borrow_media_not_available(self):
        """Test emprunt d'un média non disponible"""
        # Créer un emprunt et rendre le média non disponible
        self.livre.available = False
        self.livre.save()

        self.login_user()
        response = self.client.post(reverse('borrowing_media'), {'media_id': self.livre.id})

        # Vérifier que l'emprunt n'a pas été créé
        borrow = Borrow.objects.filter(borrower=self.member, object_id=self.livre.id).exists()
        self.assertFalse(borrow)

        # Vérifier que le message d'erreur est affiché
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), MEDIA_NOT_AVAILABLE)

    def test_borrow_media_when_limit_reached(self):
        """Test emprunt lorsque la limite d'emprunts est atteinte"""
        BorrowingRule.objects.create(active=True, limit=1)

        Borrow.objects.create(borrower=self.member, content_type=self.livre.content_type, object_id=self.livre.id)
        self.login_user()

        response = self.client.post(reverse('borrowing_media'), {'media_id': self.dvd.id})

        # Vérifier que le message d'erreur est affiché
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), BORROW_TOO_MANY)

    def test_borrow_without_selecting_media(self):
        """Test si l'utilisateur tente de soumettre sans sélectionner de média"""
        self.login_user()
        response = self.client.post(reverse('borrowing_media'), {})

        # Vérifier que le message d'erreur est affiché
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "Aucun média sélectionné.")

    def test_returning_media(self):
        """Test du retour d'un emprunt"""
        borrow = Borrow.objects.create(borrower=self.member, content_type=self.livre.content_type,
                                       object_id=self.livre.id)
        borrow.returned = True
        borrow.save()

        self.livre.refresh_from_db()
        self.assertTrue(self.livre.available)


class BorrowingMediaViewTest(TestCase):

    def setUp(self):
        """Prépare les données pour les tests"""
        self.user = User.objects.create_user(username="testuser", password="password")
        self.member = Member.objects.create(user=self.user, blocked=False)

    def login_user(self):
        """Connexion de l'utilisateur pour les tests"""
        self.client.login(username="testuser", password="password")

    def test_borrow_media_redirect_for_unauthenticated_user(self):
        """Test que les utilisateurs non connectés sont redirigés vers la page de connexion"""
        response = self.client.get(reverse('borrowing_media'))
        self.assertRedirects(response, '/login/')


@login_required
def borrowing_media(request):
    member = request.user.member
    borrow_success = False

    if request.method == 'POST':
        media_id = request.POST.get('media_id')
        if not media_id:
            messages.error(request, "Aucun média sélectionné.")
            return redirect('media_list')

        try:
            # Récupérer le média sélectionné
            selected_media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            raise Http404("Média non trouvé.")

        # Vérifier les critères d'emprunt
        valid, message = check_borrow_criteria(member, selected_media)

        if not valid:
            # Si les critères d'emprunt ne sont pas remplis, retourner une erreur
            messages.error(request, message)
            return HttpResponseBadRequest(message)

        try:
            # Créer l'emprunt si toutes les conditions sont respectées
            borrow = Borrow(
                borrower=member,
                content_type=ContentType.objects.get_for_model(selected_media),
                object_id=selected_media.id
            )
            borrow.clean()
            borrow.confirm_borrow()
            borrow_success = True
            messages.success(request, f"L'emprunt de {selected_media.name} a été effectué avec succès.")
            return redirect('borrows_list')
        except ValidationError as e:
            messages.error(request, f"Erreur de validation : {str(e)}")
            return redirect('borrowing_media')

    available_media = Media.objects.filter(available=True)
    borrows = Borrow.objects.filter(borrower=member)

    return render(request, 'personnel/borrowing_media.html', {
        'available_media': available_media,
        'borrows': borrows,
        'member': member,
        'borrow_success': borrow_success,
    })
