# personnel/services/borrow_service.py

from django.utils import timezone
from personnel.models import Borrow
from personnel.services.borrowing_rules_service import get_member_borrowing_rule
from personnel.exceptions import (
    BorrowingError,
    MediaNotAvailable,
    MaxBorrowLimitReached,
    MediaAlreadyBorrowed,
    InvalidReturnOperation,
)

def borrow_media(member, media):
    """
    Gère le processus d'emprunt d'un média par un membre, avec les règles de prêt.
    """

    # 1. Le média doit être disponible
    if not media.available:
        raise MediaNotAvailable("Ce média n'est pas disponible.")

    # 2. Aucun emprunt en retard
    if member.has_overdue_borrows():
        raise BorrowingError("Vous avez des emprunts en retard.")

    # 3. Règle d'emprunt (max)
    rule = get_member_borrowing_rule(member)
    if member.borrowed_count() >= rule.max_borrows:
        raise MaxBorrowLimitReached("Vous avez atteint le nombre maximal d'emprunts autorisé.")

    # 4. Vérifier si déjà emprunté
    if Borrow.objects.filter(borrower=member, media=media, return_date__isnull=True).exists():
        raise MediaAlreadyBorrowed("Vous avez déjà emprunté ce média.")

    # 5. Création et sauvegarde
    borrow = Borrow(borrower=member, media=media, borrow_date=timezone.now())
    borrow.clean()  # Valide l’objet (optionnel si ton modèle le gère bien)
    borrow.confirm_borrow()  # Change l'état du média
    borrow.save()
    return borrow


def return_media(member, media):
    """
    Permet à un membre de retourner un média emprunté.
    """
    try:
        borrow = Borrow.objects.get(borrower=member, media=media, return_date__isnull=True)
    except Borrow.DoesNotExist:
        raise InvalidReturnOperation("Vous n'avez pas emprunté ce média ou il est déjà retourné.")

    borrow.return_date = timezone.now()
    borrow.save()

    media.available = True
    media.save()
    return borrow
