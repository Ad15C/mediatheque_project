from authentification.forms import CustomUserCreationForm
import pytest


@pytest.mark.django_db
def test_custom_user_creation_form_invalid_passwords_non_field():
    form_data = {
        'username': 'newuser',
        'password1': 'password123',
        'password2': 'password124',  # Mots de passe non correspondants
        'email': 'newuser@example.com'
    }
    form = CustomUserCreationForm(data=form_data)
    assert not form.is_valid()  # Formulaire invalide

    # Vérifier que l'erreur est dans __all__ ou password2
    assert '__all__' in form.errors or 'password2' in form.errors

    # Vérifier que l'erreur mentionne "ne correspondent pas"
    errors = form.errors.get('__all__', []) + form.errors.get('password2', [])
    assert any("ne correspondent" in e for e in errors)


@pytest.mark.django_db
def test_custom_user_creation_form_invalid_passwords_message():
    form_data = {
        'username': 'newuser',
        'password1': 'password123',
        'password2': 'password124',  # Mots de passe non correspondants
        'email': 'newuser@example.com'
    }
    form = CustomUserCreationForm(data=form_data)
    assert not form.is_valid()  # Formulaire invalide

    # Vérifier qu'il y a bien une erreur sur 'password2'
    assert 'password2' in form.errors or '__all__' in form.errors

    # Vérifier que l'erreur dans 'password2' mentionne "Les mots de passe ne correspondent pas."
    if 'password2' in form.errors:
        assert "Les mots de passe ne correspondent pas." in form.errors['password2']
    elif '__all__' in form.errors:
        assert "Les mots de passe ne correspondent pas." in form.errors['__all__']
