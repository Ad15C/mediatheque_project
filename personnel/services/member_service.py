from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from personnel.models import Member


class MemberAlreadyExistsError(Exception):
    """Exception levée lorsqu'un membre avec le même email existe déjà."""
    pass


def add_member(form):
    if not form.is_valid():
        raise ValidationError("Le formulaire n'est pas valide.")

    cleaned_data = form.cleaned_data
    print("Cleaned data:", cleaned_data)

    username = cleaned_data['username']
    password = cleaned_data['password']
    email = cleaned_data['email']
    date_of_birth = cleaned_data['date_of_birth']
    address = cleaned_data['address']
    phone_number = cleaned_data['phone_number']
    blocked = cleaned_data['blocked']

    if Member.objects.filter(email=email).exists():
        raise MemberAlreadyExistsError("Un membre avec cet email existe déjà.")

    # Hash le mot de passe
    hashed_password = make_password(password)

    member = Member.objects.create(
        username=username,
        password=hashed_password,
        email=email,
        date_of_birth=date_of_birth,
        address=address,
        phone_number=phone_number,
        blocked=blocked
    )

    return member


def update_member(member, updated_data):
    # Exemple de validation simple
    if 'email' in updated_data and Member.objects.filter(email=updated_data['email']).exclude(id=member.id).exists():
        raise ValidationError("Un membre avec cet email existe déjà.")

    for attr, value in updated_data.items():
        setattr(member, attr, value)
    member.save()
    return member


def delete_member(member):
    member.delete()
