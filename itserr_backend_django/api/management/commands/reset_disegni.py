import os
from django.core.management.base import BaseCommand
from api.models import ImmagineReperto

class Command(BaseCommand):
    help = "Svuota completamente tutti i disegni tecnici estratti dal database e cancella i file fisici"

    def handle(self, *args, **options):
        # Filtriamo solo le immagini che sono "Disegni Tecnici" (evitando di toccare le foto reali di scavo)
        disegni = ImmagineReperto.objects.filter(didascalia__icontains="Disegno Tecnico")
        
        conteggio = disegni.count()
        
        if conteggio == 0:
            self.stdout.write(self.style.WARNING("Nessun disegno tecnico trovato nel database. Tutto pulito!"))
            return

        self.stdout.write(self.style.NOTICE(f"Trovati {conteggio} disegni. Inizio rimozione..."))

        eliminati_file = 0
        for img in disegni:
            # Recuperiamo il percorso assoluto del file sul disco
            if img.file_immagine and hasattr(img.file_immagine, 'path'):
                path_file = img.file_immagine.path
                if os.path.exists(path_file):
                    try:
                        os.remove(path_file)
                        eliminati_file += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Impossibile eliminare il file {path_file}: {e}"))

            # Elimina la riga dal Database
            img.delete()

        self.stdout.write(self.style.SUCCESS(
            f"\n[RESET COMPLETATO]\n"
            f"🗑️ Righe cancellate dal DB: {conteggio}\n"
            f"📂 File fisici rimossi dal Mac: {eliminati_file}"
        ))