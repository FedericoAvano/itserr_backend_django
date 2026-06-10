# api/management/commands/link_models_to_reperti.py

import os
from django.core.management.base import BaseCommand
from api.models import Reperto

class Command(BaseCommand):
    help = 'Aggancia automaticamente i modelli 3D ai reperti corrispondenti usando il codice reperto dal nome del file OBJ.'

    def handle(self, *args, **options):
        # Percorso alla cartella dove sono salvati i tuoi modelli OBJ
        # DEVI AGGIORNARE QUESTO PERCORSO CON IL VALORE ASSOLUTO E CORRETTO SUL TUO COMPUTER.
        media_root = '/path/to/your/project/itserr_backend_django/media/models/obj_files/'
        
        self.stdout.write(self.style.SUCCESS("Avvio del processo di aggancio modelli-reperti..."))
        
        reperti_con_modello_agganciato = 0
        reperti_non_agganciati = 0
        
        for reperto in Reperto.objects.all():
            codice = reperto.codice_inventario_patrimoniale
            
            if not codice:
                self.stdout.write(self.style.WARNING(f"⚠️ Attenzione: Reperto senza codice inventario, ignorato."))
                continue

            # Controlla se il modello esiste nella cartella media
            obj_path = os.path.join(media_root, f"{codice}.obj")
            
            if os.path.exists(obj_path):
                # Se il file esiste, aggiorna il campo 'mymodel' con il percorso relativo che usa il MEDIA_URL
                relative_path = f"models/obj_files/{codice}.obj"
                
                if reperto.mymodel != relative_path:
                    reperto.mymodel = relative_path
                    reperto.save()
                    self.stdout.write(self.style.SUCCESS(f"✅ Successo: Agganciato il modello 3D al reperto '{codice}'."))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️ Attenzione: Il reperto '{codice}' ha già un modello 3D agganciato."))
                reperti_con_modello_agganciato += 1
            else:
                self.stdout.write(f"❌ Fallito: Nessun file modello trovato per il reperto '{codice}'.")
                reperti_non_agganciati += 1

        self.stdout.write(self.style.SUCCESS(f"Processo completato. Totale reperti agganciati: {reperti_con_modello_agganciato}. Totale non agganciati: {reperti_non_agganciati}."))