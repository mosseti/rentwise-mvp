import os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from accounts.models import Profile


class Command(BaseCommand):
    help = 'Create or update the production RentWise platform admin from environment variables.'

    def handle(self, *args, **options):
        username = os.getenv('ADMIN_USERNAME')
        email = os.getenv('ADMIN_EMAIL', '')
        password = os.getenv('ADMIN_PASSWORD')

        if not username or not password:
            raise CommandError('Set ADMIN_USERNAME and ADMIN_PASSWORD before running this command.')

        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.email = email or user.email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        user.profile.role = Profile.ADMIN
        user.profile.approval_status = Profile.APPROVED
        user.profile.phone_verified = True
        user.profile.save(update_fields=['role', 'approval_status', 'phone_verified'])

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} platform admin: {username}'))
