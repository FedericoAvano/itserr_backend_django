from django.core.management.base import BaseCommand
from django.db import connection
from api.models import MyModel  # aggiorna con il percorso corretto

class Command(BaseCommand):
    help = "Cancella MyModel e resetta gli ID (i file vengono rimossi automaticamente grazie a django-cleanup)."

    def handle(self, *args, **kwargs):
        # Cancella tutti gli oggetti (django-cleanup elimina automaticamente i file)
        MyModel.objects.all().delete()
        self.stdout.write(self.style.WARNING("Tutti i modelli cancellati, file rimossi automaticamente."))

        # Reset ID
        model_table = MyModel._meta.db_table
        with connection.cursor() as cursor:
            vendor = connection.vendor
            if vendor == "postgresql":
                cursor.execute(f"ALTER SEQUENCE {model_table}_id_seq RESTART WITH 1;")
                self.stdout.write(self.style.SUCCESS("Sequence PostgreSQL resettata."))
            elif vendor == "sqlite":
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{model_table}';")
                self.stdout.write(self.style.SUCCESS("Sequence SQLite resettata."))
            elif vendor == "mysql":
                cursor.execute(f"ALTER TABLE {model_table} AUTO_INCREMENT = 1;")
                self.stdout.write(self.style.SUCCESS("Auto-increment MySQL resettato."))
            else:
                self.stdout.write(self.style.ERROR("Database non supportato per il reset automatico."))
