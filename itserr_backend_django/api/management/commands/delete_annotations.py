from django.core.management.base import BaseCommand
from django.db import connection
from api.models import Annotazione

class Command(BaseCommand):
    help = 'Elimina tutte le annotazioni e resetta il contatore ID'

    def handle(self, *args, **options):
        # 1. Conta quante ce ne sono prima di eliminare
        count = Annotazione.objects.count()

        if count == 0:
            self.stdout.write(self.style.WARNING("Non ci sono annotazioni da eliminare."))
            return

        # 2. Eliminazione massiva
        Annotazione.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Eliminate {count} annotazioni."))

        # 3. Reset dell'ID (Autoincrement)
        # Funziona per SQLite (standard in dev) e PostgreSQL
        with connection.cursor() as cursor:
            table_name = Annotazione._meta.db_table
            
            if connection.vendor == 'sqlite':
                # SQLite tiene i contatori in questa tabella di sistema
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}';")
                self.stdout.write(self.style.SUCCESS(f"Contatore ID per '{table_name}' resettato a 1 (SQLite)."))
            
            elif connection.vendor == 'postgresql':
                # PostgreSQL usa le 'sequences'
                cursor.execute(f"ALTER SEQUENCE {table_name}_id_seq RESTART WITH 1;")
                self.stdout.write(self.style.SUCCESS(f"Contatore ID per '{table_name}' resettato a 1 (Postgres)."))

        self.stdout.write(self.style.SUCCESS("Operazione completata con successo!"))