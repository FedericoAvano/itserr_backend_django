from django.core.management.base import BaseCommand
from django.db import connection
from api.models import Reperto

class Command(BaseCommand):
    help = "Cancella tutti i reperti e resetta gli ID a partire da 1"

    def handle(self, *args, **kwargs):
        # Cancella tutti i reperti
        Reperto.objects.all().delete()
        self.stdout.write(self.style.WARNING("Tutti i reperti sono stati cancellati."))

        # Reset della sequenza ID in base al database
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute("ALTER SEQUENCE api_reperto_id_seq RESTART WITH 1;")
                self.stdout.write(self.style.SUCCESS("Sequenza PostgreSQL resettata a 1."))
            elif connection.vendor == 'sqlite':
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='api_reperto';")
                self.stdout.write(self.style.SUCCESS("Sequenza SQLite resettata a 1."))
            elif connection.vendor == 'mysql':
                cursor.execute("ALTER TABLE api_reperto AUTO_INCREMENT = 1;")
                self.stdout.write(self.style.SUCCESS("Auto Increment MySQL resettato a 1."))
            else:
                self.stdout.write(self.style.ERROR("Database non supportato per il reset automatico."))
