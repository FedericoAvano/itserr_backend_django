from django.apps import AppConfig
from django.conf import settings
from django.core.management import call_command
import sys
import logging
import threading
import time

logger = logging.getLogger(__name__)

# Flag globale per prevenire l'esecuzione multipla (tipica con runserver/daphne auto-reload)
IMPORTER_RAN = False

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        global IMPORTER_RAN
        
        # L'importazione dei segnali deve avvenire qui per evitare AppRegistryNotReady
        import api.signals
        
        # Definisci lo stato attuale
        current_env = getattr(settings, 'ENVIRONMENT', 'development')
        
        # 1. Controlli di sicurezza di base
        is_safe_to_run = not any(
            arg in sys.argv for arg in ['migrate', 'shell', 'createsuperuser', 'help']
        )
        
        # 2. Controlla se siamo in un comando di avvio del server principale
        is_server_start = any(
            command in sys.argv[0] or command in sys.argv for command in ('daphne', 'runserver', 'gunicorn')
        )

        # 3. Logica Condizionale: Esegui solo all'avvio del server, una volta sola
        if (is_server_start or current_env == 'development') and 'runworker' not in sys.argv and is_safe_to_run and not IMPORTER_RAN:
            IMPORTER_RAN = True
            logger.info("Avvio del processo di sincronizzazione reperti in un thread separato...")
            
            # Lancia il task in un thread separato
            thread = threading.Thread(target=self._start_sync_task)
            thread.daemon = True 
            thread.start()
            
            logger.info("Server avviato, la sincronizzazione procede in background.")

    def _start_sync_task(self):
        """Funzione helper eseguita nel thread con logica di retry per SQLite."""
        logger.info("--- Sincronizzazione Reperti: Avvio task sincrono isolato ---")
        
        # Attesa iniziale per lasciare che il server completi le operazioni di boot I/O
        time.sleep(15)
        
        max_retries = 3
        for i in range(max_retries):
            try:
                logger.info(f"--- Tentativo di sincronizzazione {i+1}/{max_retries} ---")
                call_command('import_reperti')
                logger.info("--- Sincronizzazione Reperti completata con successo ---")
                break
            except Exception as e:
                # Se SQLite è bloccato, attendi un tempo crescente e riprova
                if "locked" in str(e).lower():
                    wait_time = (i + 1) * 20
                    logger.warning(f"Database bloccato (SQLite lock), riprovo tra {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Errore critico durante la sincronizzazione: {e}")
                    break