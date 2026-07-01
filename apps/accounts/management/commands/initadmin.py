import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates or updates a superuser account from environment variables if set.'

    def handle(self, *args, **options):
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL') or os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD') or os.environ.get('ADMIN_PASSWORD')
        first_name = os.environ.get('DJANGO_SUPERUSER_FIRST_NAME', 'Admin')
        last_name = os.environ.get('DJANGO_SUPERUSER_LAST_NAME', 'User')

        if not email or not password:
            self.stdout.write(self.style.WARNING(
                'DJANGO_SUPERUSER_EMAIL / ADMIN_EMAIL or password environment variables not set. Skipping auto admin creation.'
            ))
            return

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'is_email_verified': True,
            }
        )

        if not created:
            user.is_staff = True
            user.is_superuser = True
            user.role = 'admin'
            user.is_active = True

        user.set_password(password)
        user.save()

        action = 'Created new' if created else 'Updated existing'
        self.stdout.write(self.style.SUCCESS(f'{action} superuser: {email}'))
