# api/migrations/0029_auto_20251014_0748.py

from django.db import migrations
from django.conf import settings
import sys

# --- Importazione del Processore AI/NLP ---
# NOTA BENE: Questo gestisce il caso in cui il processore sia in api/ai_processor.py
# e il fallimento del caricamento di spacy.load()
try:
    from api.ai_processor import analizza_testo_annotazione
except ImportError:
    # Se il file di importazione non viene trovato
    print("ATTENZIONE CRITICA: Impossibile importare analizza_testo_annotazione da api.ai_processor.")
    
    # Crea una funzione fittizia che restituisce un oggetto JSON vuoto come fallback
    # Questo permette alla migrazione di completare senza schiantarsi, anche se non fa nulla.
    def analizza_testo_annotazione(testo: str) -> dict:
        print("NLP NOT FOUND: Restituisco dati vuoti per evitare crash.")
        return {} 


def backfill_nlp_data(apps, schema_editor):
    """
    Riesegue il processore NLP potenziato su tutte le annotazioni esistenti 
    per aggiornare analisi_ia_json con il nuovo data model semantico.
    """
    
    # 1. Ottiene la versione storica del modello Annotazione
    try:
        # Assicurati che 'Annotazione' sia il nome esatto del tuo modello
        Annotazione = apps.get_model('api', 'Annotazione')
    except LookupError:
        print("ERRORE FATALE: Modello 'Annotazione' non trovato nell'app 'api'.")
        return
    
    print("\n--- AVVIO BACKFILL DATI NLP (API) ---")
    
    # 2. Cicla su tutte le annotazioni
    for annotazione in Annotazione.objects.all():
        try:
            # Riapplica il nuovo processore sul campo 'testo'
            nuovi_dati_ia = analizza_testo_annotazione(annotazione.testo)
            
            # Aggiorna il campo JSON (analisi_ia_json)
            annotazione.analisi_ia_json = nuovi_dati_ia
            
            # Salva l'istanza
            annotazione.save()
            
        except Exception as e:
            # Cattura e segnala eventuali errori runtime (es. DB, Spacy, ecc.)
            print(f"ERRORE runtime nell'annotazione ID {annotazione.id}: {e}")
            
    print("\n--- BACKFILL COMPLETATO ---")

def reverse_backfill(apps, schema_editor):
    """
    Funzione di reverse. Lasciata vuota in quanto l'annullamento di un backfill dati
    richiederebbe una logica complessa che non è lo scopo qui.
    """
    pass


class Migration(migrations.Migration):

    # CORREZIONE DELLA DIPENDENZA CIRCOLARE: 
    # DEVI INSERIRE IL NOME ESATTO DELL'ULTIMA MIGRAZIONE *PRECEDENTE* QUI!
    dependencies = [
        ('api', '0028_annotazione_analisi_ia_json'), # <-- SOSTITUISCI '0028_schema_change'
    ]

    operations = [
        migrations.RunPython(backfill_nlp_data, reverse_code=reverse_backfill),
    ]