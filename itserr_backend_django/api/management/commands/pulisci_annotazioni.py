# File: api/management/commands/pulisci_annotazioni.py

from django.core.management.base import BaseCommand
from django.db import connection, transaction
# RIMOZIONE: Rimosso 'from api.models import Annotazione' da qui

class Command(BaseCommand):
    help = 'Elimina tutte le annotazioni e resetta il contatore degli ID.'

    def handle(self, *args, **kwargs):
        # 🚨 AGGIUNTO: Importazione del modello spostata all'interno di handle()
        from api.models import Annotazione 

        self.stdout.write("Eliminazione di tutte le annotazioni...")

        # Utilizzo di una transazione per garantire che le operazioni siano atomiche
        with transaction.atomic():
            # Elimina tutti gli oggetti Annotazione
            # Nota: Questa operazione non scatena i segnali post_delete,
            # cosa che è un bene in questo contesto di pulizia radicale.
            deleted_count, _ = Annotazione.objects.all().delete()
            
            # Reset del contatore degli ID basato sul tipo di database
            db_engine = connection.vendor
            table_name = Annotazione._meta.db_table

            # L'eliminazione tramite .objects.all().delete() non resetta l'ID.
            # Dobbiamo forzare il reset della sequenza/auto-incremento.

            if db_engine == 'sqlite':
                with connection.cursor() as cursor:
                    # Per SQLite, dobbiamo resettare la sequenza manualmente
                    # Poiché Annotazione.objects.all().delete() non svuota sqlite_sequence,
                    # il reset corretto è solo aggiornare la sequenza. 
                    # Se Annotazione.objects.all().delete() non basta, 
                    # puoi optare per: cursor.execute(f"DELETE FROM {table_name}")
                    cursor.execute(f"UPDATE sqlite_sequence SET seq=0 WHERE name='{table_name}'")
            elif db_engine == 'postgresql':
                with connection.cursor() as cursor:
                    # Per PostgreSQL, TRUNCATE è l'opzione migliore,
                    # e TRUNCATE... CASCADE è più sicuro se ci sono chiavi esterne.
                    cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")
            elif db_engine == 'mysql':
                with connection.cursor() as cursor:
                    # Per MySQL, TRUNCATE resetta automaticamente l'autoincremento
                    cursor.execute(f"TRUNCATE TABLE {table_name}")
            else:
                self.stdout.write(self.style.WARNING("Il reset del contatore ID non è supportato per questo database, ma le annotazioni sono state eliminate."))
                
        self.stdout.write(self.style.SUCCESS(f"✔ Eliminazione e reset completato! Sono state rimosse {deleted_count} annotazioni."))