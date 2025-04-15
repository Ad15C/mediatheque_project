from personnel.models import BorrowingRule


def get_active_borrowing_rules():
    return BorrowingRule.objects.filter(is_active=True).order_by('-id')

def get_member_borrowing_rule(member):
    # Rechercher la règle spécifique en fonction du type de membre ou d'autres critères
    return BorrowingRule.objects.filter(member_type=member.type, is_active=True).first()




