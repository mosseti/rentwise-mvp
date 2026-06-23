from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create a timestamped JSON backup of core RentWise database records.'

    def handle(self, *args, **options):
        backup_dir = Path(getattr(settings, 'BACKUP_DIR', settings.BASE_DIR / 'backups'))
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = timezone.now().strftime('%Y%m%d-%H%M%S')
        path = backup_dir / f'rentwise-backup-{stamp}.json'
        with path.open('w', encoding='utf-8') as output:
            call_command(
                'dumpdata',
                'auth.User',
                'accounts.Profile',
                'rentals.Area',
                'rentals.Building',
                'rentals.Unit',
                'rentals.UnitImage',
                'rentals.ViewingRequest',
                'rentals.CachedPlace',
                stdout=output,
                indent=2,
            )
        self.stdout.write(self.style.SUCCESS(f'Backup written to {path}'))
