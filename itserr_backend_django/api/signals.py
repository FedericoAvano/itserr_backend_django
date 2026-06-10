# api/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
# Assicurati che MyModel, Reperto, Annotazione siano importati dal tuo models.py
from .models import MyModel, Reperto, Annotazione 
# Assicurati che esista un modulo ai_processor con la funzione analizza_testo_annotazione
from .ai_processor import analizza_testo_annotazione 
import os

# =================================================================================
# 1. LOGICA ESISTENTE: Collegamento MyModel <-> Reperto
# =================================================================================

@receiver(post_save, sender=MyModel)
def cerca_e_collega_reperto(sender, instance, created, **kwargs):
    """
    Cerca un Reperto corrispondente basato sul nome del file OBJ e lo collega al MyModel.
    (Omessa logica interna per brevità, si assume che sia quella fornita)
    """
    if created:
        if instance.obj_file:
            filename = os.path.basename(instance.obj_file.name)
            codice_reperto = os.path.splitext(filename)[0]

            try:
                reperto = Reperto.objects.get(codice=codice_reperto)
                if not getattr(reperto, 'mymodel', None):
                    reperto.mymodel = instance
                    reperto.save(update_fields=['mymodel']) 
                    print(f"✅ Successo: Reperto '{codice_reperto}' collegato al modello 3D.")
                # else: ... (logica di avviso)
            except Reperto.DoesNotExist:
                print(f"❌ Errore: Nessun reperto trovato con il codice '{codice_reperto}'.")


# =================================================================================
# 2. NUOVA LOGICA: Analisi AI Real-Time per Annotazione
# =================================================================================

@receiver(post_save, sender=Annotazione)
def analizza_annotazione_realtime(sender, instance, created, **kwargs):
    """
    Esegue l'analisi AI (NLP) sul testo dell'annotazione subito dopo il salvataggio.
    Aggiorna analisi_ia_json in modo atomico per non causare loop ricorsivi.
    """
    # Esegui l'analisi se è una nuova annotazione O se l'analisi IA è vuota
    if created or instance.analisi_ia_json is None or instance.analisi_ia_json == {}:
        
        print(f"💡 Avvio analisi IA real-time per Annotazione ID {instance.pk}...")
        
        try:
            # 1. Esecuzione dell'analisi
            risultati = analizza_testo_annotazione(instance.testo)
            
            # 2. Logica di Fallback/Forzatura (come da requisiti)
            if risultati.get('luogo_ritrovamento') is None and 'pompei' in instance.testo.lower():
                risultati['luogo_ritrovamento'] = 'pompei'
                
                oggetti_puliti = [o for o in risultati.get('oggetti_rilevati', []) 
                                  if o and o.lower() not in ['pompei', 'sito']]
                
                if 'vaso' in instance.testo.lower() and 'vaso' not in oggetti_puliti:
                     oggetti_puliti.append('vaso')
                     
                risultati['oggetti_rilevati'] = list(set([o.lower() for o in oggetti_puliti])) 
            # -------------------------------------------------------------

            # 3. Aggiornamento atomico del campo (ESSENZIALE)
            Annotazione.objects.filter(pk=instance.pk).update(analisi_ia_json=risultati)
            
            print(f"✅ Analisi IA completata e salvata per Annotazione ID {instance.pk}.")
            
        except Exception as e:
            print(f"❌ Errore grave durante l'analisi NLP per Annotazione ID {instance.pk}: {e}")