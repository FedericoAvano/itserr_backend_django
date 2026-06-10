from django.core.management.base import BaseCommand
from api.models import Reperto

class Command(BaseCommand):
    help = "Conta quanti reperti ci sono"

    def handle(self, *args, **kwargs):
        count = Reperto.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Totale reperti salvati: {count}"))
