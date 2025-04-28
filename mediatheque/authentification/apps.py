from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentification'

    def ready(self):
        from django.contrib.auth.models import Group, Permission
        from django.contrib.contenttypes.models import ContentType
        from .models import CustomUser

        def create_groups_and_permissions(sender, **kwargs):
            staff_group, _ = Group.objects.get_or_create(name='staff')
            client_group, _ = Group.objects.get_or_create(name='client')

            content_type = ContentType.objects.get_for_model(CustomUser)

            permissions_staff = [
                ('can_add_member', 'Can add members'),
                ('can_update_member', 'Can update members'),
                ('can_view_members', 'Can view members'),
                ('can_add_media', 'Can add media'),
                ('can_return_media', 'Can return media'),
                ('can_borrow_media', 'Can borrow media'),
                ('can_view_media', 'Can view media'),
            ]

            for codename, name in permissions_staff:
                perm, created = Permission.objects.get_or_create(
                    codename=codename,
                    name=name,
                    content_type=content_type,
                )
                if created:
                    staff_group.permissions.add(perm)

                if codename == 'can_view_media':  # La permission partagée
                    client_group.permissions.add(perm)

        post_migrate.connect(create_groups_and_permissions, sender=self)
