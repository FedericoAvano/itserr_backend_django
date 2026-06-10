import os
import fitz
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Debug OCR: Mostra esattamente cosa legge PyMuPDF sulla tavola A0"

    def handle(self, *args, **options):
        pdf_path = os.path.join(settings.BASE_DIR, "didascalie_A0.pdf")
        
        if not os.path.exists(pdf_path):
            self.stdout.write(self.style.ERROR(f"File {pdf_path} non trovato."))
            return

        doc = fitz.open(pdf_path)
        pagina = doc[0]
        parole = pagina.get_text("words")
        
        self.stdout.write(self.style.NOTICE("--- INIZIO DIRETTO LETTURA COORD OCR ---"))
        
        mappa_forzatura = {
            'I': '1', 'L': '1', 'T': '1', 'N': '1', 'M': '1',
            'O': '0', 'Q': '0', 'U': '0', 'C': '0',
            'S': '5', 'B': '8', 'Z': '2', 'A': '4'
        }

        for p in parole:
            testo = p[4].upper()
            if testo.startswith("MO") and len(testo) >= 3:
                parte_letta = testo[2:]
                parte_corretta = "".join([mappa_forzatura.get(char, char) for char in parte_letta])
                codice_generato = f"MO{parte_corretta}"
                
                # Stampiamo la stringa originale, quella convertita e la posizione (X0, Y0, X1, Y1)
                print(f"Letto nel PDF: '{p[4]}' -> Convertito in: '{codice_generato}' | Posizione: X=({int(p[0])}-{int(p[2])}), Y=({int(p[1])}-{int(p[3])})")

        self.stdout.write(self.style.NOTICE("--- FINE LETTURA ---"))