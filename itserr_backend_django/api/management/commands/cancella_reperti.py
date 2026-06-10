from django.core.management.base import BaseCommand
from api.models import Reperto

class Command(BaseCommand):
    help = "Cancella tutti i reperti dal database"

    def handle(self, *args, **kwargs):
        count, _ = Reperto.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Cancellati {count} reperti dal database"))

