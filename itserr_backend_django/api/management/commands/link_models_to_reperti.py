# api/management/commands/link_models_to_reperti.py

from django.core.management.base import BaseCommand
from api.models import MyModel, Reperto
import os

class Command(BaseCommand):
    help = 'Aggancia automaticamente i modelli 3D ai reperti corrispondenti usando il codice reperto dal nome del file OBJ.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Avvio del processo di mappatura modelli-reperti..."))

        # 1. Trova tutti i modelli 3D che non sono ancora collegati a un reperto
        modelli_non_collegati = MyModel.objects.all()

        if not modelli_non_collegati:
            self.stdout.write(self.style.WARNING("Nessun modello 3D da controllare trovato."))
            return

        for modello in modelli_non_collegati:
            # Assicurati che l'URL del file sia presente
            if not modello.obj_file:
                self.stdout.write(self.style.WARNING(f"Modello con ID {modello.id} non ha un file OBJ, ignorato."))
                continue

            # 2. Estrai il codice del reperto dal nome del file del modello
            # Esempio: 'media/modelli/MO1.obj' -> 'MO1'
            filename = os.path.basename(modello.obj_file.name)
            codice_reperto = os.path.splitext(filename)[0]

            self.stdout.write(f"Cercando un reperto per il modello '{modello.name}' con codice '{codice_reperto}'...")

            try:
                # 3. Cerca il reperto corrispondente e se non è già collegato
                # al tuo mymodel
                reperto_corrispondente = Reperto.objects.get(codice=codice_reperto)
                
                # Controlla se il reperto è già collegato a un mymodel
                if reperto_corrispondente.mymodel:
                    self.stdout.write(self.style.WARNING(f"⚠️ Attenzione: il reperto '{codice_reperto}' è già collegato al modello ID {reperto_corrispondente.mymodel.id}."))
                    continue

                # 4. Aggancia il reperto al modello
                reperto_corrispondente.mymodel = modello
                reperto_corrispondente.save()

                self.stdout.write(self.style.SUCCESS(f"✅ Successo: Reperto '{codice_reperto}' collegato al modello ID {modello.id}."))
            except Reperto.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Fallito: Nessun reperto trovato con il codice '{codice_reperto}'."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Errore sconosciuto durante il collegamento del reperto '{codice_reperto}': {e}"))

        self.stdout.write(self.style.SUCCESS("Processo di mappatura completato."))