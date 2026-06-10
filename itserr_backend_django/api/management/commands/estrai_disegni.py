import os
import io
import warnings
import fitz  # PyMuPDF
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.base import ContentFile
from api.models import Reperto, ImmagineReperto

warnings.simplefilter('ignore', Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = None

class Command(BaseCommand):
    help = "PRODUZIONE: Ritaglia tutti i disegni dal PDF e li mappa sui codici corti del DB"

    def handle(self, *args, **options):
        pdf_path = os.path.join(settings.BASE_DIR, "didascalie_A0.pdf")
        
        if not os.path.exists(pdf_path):
            self.stdout.write(self.style.ERROR(f"File {pdf_path} non trovato."))
            return

        # 🧹 PRIMA DI COMINCIARE: Svuotiamo i vecchi record per evitare sovrascritture fantasma
        self.stdout.write(self.style.NOTICE("Pulizia record orfani precedenti in corso..."))
        ImmagineReperto.objects.filter(didascalia__icontains="Disegno").delete()

        doc = fitz.open(pdf_path)
        pagina = doc[0]
        
        zoom = 4  
        mat = fitz.Matrix(zoom, zoom)
        pix = pagina.get_pixmap(matrix=mat)
        immagine_totale = Image.open(io.BytesIO(pix.tobytes("png")))

        disegni_vettoriali = pagina.get_drawings()
        parole = pagina.get_text("words")
        
        creati = 0
        saltati_db = 0
        
        mappa_forzatura = {
            'I': '1', 'L': '1', 'T': '1', 'N': '1', 'M': '1',
            'O': '0', 'Q': '0', 'U': '0', 'C': '0',
            'S': '5', 'B': '8', 'Z': '2', 'A': '4'
        }

        self.stdout.write(self.style.NOTICE("Avvio elaborazione e mappatura codici..."))

        for p in parole:
            testo_originale = p[4].strip()
            testo = testo_originale.upper()
            
            # Blocca i numeri di tavola isolati in cima
            if testo.isdigit() and len(testo) <= 2:
                continue
                
            if testo.startswith("MO") and len(testo) >= 3:
                parte_letta = testo[2:]
                parte_corretta = "".join([mappa_forzatura.get(char, char) for char in parte_letta])
                
                # Codice letto completo (es. MO1172)
                codice_pdf = f"MO{parte_corretta}"
                
                # 🛠️ STRATEGIA DI MAPPATURA:
                # Se a DB i codici sono corti (es. "MO1" invece di "MO1172"), proviamo a cercare prima il codice corto.
                # Prendiamo "MO" + la prima cifra numerica (es. "MO1172" -> "MO1")
                codice_corto = codice_pdf[:3] 
                
                reperto_db = None
                # Tentativo 1: Cerchiamo il codice esatto per esteso
                try:
                    reperto_db = Reperto.objects.get(codice=codice_pdf)
                    codice_effettivo = codice_pdf
                except Reperto.DoesNotExist:
                    # Tentativo 2: Fallito il primo, cerchiamo con il codice corto esistente a DB
                    try:
                        reperto_db = Reperto.objects.get(codice=codice_corto)
                        codice_effettivo = codice_corto
                    except Reperto.DoesNotExist:
                        saltati_db += 1
                        continue
                
                x0_testo, y0_testo, x1_testo, y1_testo = p[0], p[1], p[2], p[3]
                centro_x_testo = (x0_testo + x1_testo) / 2

                elementi_trovati_sotto = []
                for d in disegni_vettoriali:
                    rect_disegno = d["rect"]
                    
                    if rect_disegno.y0 > y1_testo and ((rect_disegno.x0 - 20) <= centro_x_testo <= (rect_disegno.x1 + 20)):
                        if rect_disegno.width < 300 and rect_disegno.height < 300:
                            elementi_trovati_sotto.append(rect_disegno)

                if elementi_trovati_sotto:
                    elementi_trovati_sotto.sort(key=lambda r: r.y0)
                    primo_elemento = elementi_trovati_sotto[0]
                    
                    y0_box = primo_elemento.y0
                    x0_box = min([r.x0 for r in elementi_trovati_sotto[:5]])
                    x1_box = max([r.x1 for r in elementi_trovati_sotto[:5]])
                    y1_box = max([r.y1 for r in elementi_trovati_sotto[:5]])
                    
                    padding_orizzontale = 20
                    padding_superiore = 0      
                    padding_inferiore = 55     
                    
                    crop_x0 = x0_box - padding_orizzontale
                    crop_y0 = y0_box - padding_superiore
                    crop_x1 = x1_box + padding_orizzontale
                    crop_y1 = y1_box + padding_inferiore
                    
                    left = max(0, crop_x0 * zoom)
                    top = max(0, crop_y0 * zoom)
                    right = min(immagine_totale.width, crop_x1 * zoom)
                    bottom = min(immagine_totale.height, crop_y1 * zoom)
                    
                    immagine_ritagliata = immagine_totale.crop((left, top, right, bottom))
                    
                    buffer_immagine = io.BytesIO()
                    immagine_ritagliata.save(buffer_immagine, format="PNG")
                    nome_file = f"{codice_effettivo}_disegno_tecnico.png"
                    content_file = ContentFile(buffer_immagine.getvalue(), name=nome_file)
                    
                    nuova_immagine = ImmagineReperto(
                        reperto=reperto_db,
                        didascalia="Disegno Tecnico (Profilo/Scala)"
                    )
                    nuova_immagine.file_immagine.save(nome_file, content_file, save=True)
                    
                    self.stdout.write(self.style.SUCCESS(f" -> [DB SALVATO] Associato disegno di {codice_pdf} al reperto DB: {codice_effettivo}"))
                    creati += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n[ELABORAZIONE COMPLETATA]\n"
            f"✅ Nuovi disegni associati a DB: {creati}\n"
            f"⚠️ Codici saltati perché non presenti nel DB: {saltati_db}"
        ))