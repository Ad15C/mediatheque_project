from django.contrib.messages.context_processors import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from personnel.models import BorrowingRule, Borrow
from personnel.messages import BORROW_BLOCKED ,BORROW_TOO_MANY ,MEDIA_NOT_AVAILABLE ,MEMBER_HAS_DELAY ,BORROW_MESSAGE ,BORROW_SUCCESS
from django.db import transaction
import logging


logger = logging.getLogger(__name__)


# Fonction pour effectuer l'emprunt
def validate_borrowing(member, media):
    borrowing_rule = get_active_borrowing_rules().first()
    if borrowing_rule is None:
        return False, BORROW_MESSAGE

    # Exemple d'ajout de règles spécifiques par type de média
    if media.__class__ == Livre:
        if borrowing_rule.max_livres < member.get_borrowed_media().filter(media_type='livre').count():
            return False, BORROW_TOO_MANY

    if media.__class__ == DVD:
        if borrowing_rule.max_dvds < member.get_borrowed_media().filter(media_type='dvd').count():
            return False, BORROW_TOO_MANY

    if media.__class__ == CD:
        if borrowing_rule.max_cds < member.get_borrowed_media().filter(media_type='cd').count():
            return False, BORROW_TOO_MANY

    # Validation générale de l'emprunt (tous types de média confondus)
    if member.get_borrowed_media().count() >= borrowing_rule.max_items:
        return False, BORROW_TOO_MANY

    if not media.available:
        return False, MEDIA_NOT_AVAILABLE

    return True, BORROW_SUCCESS


# Fonction pour retourner un emprunt
def return_media(borrow_id, member):
    try:
        borrow = Borrow.objects.get(id=borrow_id, borrower=member)
    except Borrow.DoesNotExist:
        return JsonResponse({'error': 'Emprunt non trouvé ou non associé à ce membre.'}, status=404)

    if borrow.is_overdue():
        return JsonResponse({'error': 'Média en retard, vous devez le retourner avant de pouvoir le remettre.'}, status=400)

    try:
        borrow.mark_as_returned()
        borrow.media.available = True
        borrow.media.save()
        return JsonResponse({'message': 'Média retourné avec succès.'})
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)


# Fonction pour afficher les emprunts en retard du membre
def get_borrows_to_return(member):
    borrows = Borrow.objects.filter(date_effective_return__isnull=True, borrower=member)
    return borrows
