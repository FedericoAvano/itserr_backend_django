import requests
import json
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import (
    Reperto,
    Stemma,
    Iscrizione,
    Bibliografia,
    DocumentazioneFotografica,
    CondizioneGiuridica,
    Compilazione,
    ImmagineReperto,     # NUOVO
    Misura,              # NUOVO
    ScavoArcheologico,   # NUOVO
)

# --- Costanti di Configurazione ---
BASE_URL = "https://museoscerrato.unior.it/restSipor/rest/json/fun/visualizzaScheda"
PREFIX = "MO"
MAX_ID_CHECK = 9999              # Limite teorico massimo da controllare.
MAX_EMPTY_CONSECUTIVE = 10       # Interrompe il ciclo dopo 10 reperti consecutivi non trovati
HEADERS = {'accept': 'application/json'}

# Nuovi campi mappati nel modello Reperto
NEW_REPERTO_FIELDS = {
    'OGT': "tipologia_funzionale",          # NUOVO
    'LDCS': "specifiche_collocazione",      # NUOVO
    'STCC': "stato_conservazione",
    'NSC': "notizie_storico_critiche",
    'INPP': "provenienza",
}
# ---------------------------------


class Command(BaseCommand):
    help = f"Importa e aggiorna i reperti {PREFIX} da API esterna con interruzione dinamica dopo {MAX_EMPTY_CONSECUTIVE} reperti vuoti consecutivi."

    def parse_json_data(self, data):
        """
        Estrae e organizza i dati da JSON per i vari modelli.
        Restituisce None se mancano chiavi essenziali ('jsonData', 'dettaglio').
        """
        try:
            dettaglio = data['jsonData']['dettaglio']
            immagini_raw = data['jsonData'].get('immagini', [])
        except KeyError:
            # Dati non validi o mancanti (non considerati 404)
            return None
        
        dettaglio_map_flat = {item.get("codiceCampo"): item.get("valore") for item in dettaglio}
        
        parsed_data = {
            "reperto_main": {},
            "stemmi": [],
            "iscrizioni": [],
            "bibliografia": [],
            "documentazione_fotografica": [],
            "condizione_giuridica": {},
            "compilazione": {},
            "immagini": [],              # NUOVO: per ImmagineReperto
            "misure_dettagliate": [],    # NUOVO: per Misura
            "scavi": [],                 # NUOVO: per ScavoArcheologico
        }
        
        # Mappatura principale (campi del modello Reperto)
        mapping_main = {
            "OGD": "definizione", "CTG": "categoria_materiale",
            "CLP": "classe_produzione", "PVCR": "regione",
            "PVCP": "provincia", "PVCC": "comune",
            "LDCN": "denominazione_museo", "LDCU": "indirizzo",
            "LDCM": "denominazione_raccolta", "LDCZ": "sezione",
            "DES": "descrizione", "MTC": "materia_tecnica",
            "DTR": "riferimento_cronologico", "RES": "specifiche_reperimento",
            "INPO": "nome_inventario", "INPC": "codice_inventario_patrimoniale",
            "INPD": "data_inventario",
            **NEW_REPERTO_FIELDS # Aggiunge i campi OGT, LDCS, STCC, NSC, INPP
        }
        
        for codice, field in mapping_main.items():
            parsed_data["reperto_main"][field] = dettaglio_map_flat.get(codice)
        
        # Imposta il campo "codice" (MOxxx) dal campo d'inventario
        if "codice_inventario_patrimoniale" in parsed_data["reperto_main"]:
            parsed_data["reperto_main"]["codice"] = parsed_data["reperto_main"]["codice_inventario_patrimoniale"]
        
        # --- Mappatura OneToOne (CondizioneGiuridica e Compilazione) ---
        parsed_data["condizione_giuridica"]["nome"] = dettaglio_map_flat.get("ACQN")
        parsed_data["condizione_giuridica"]["tipo_acquisizione"] = dettaglio_map_flat.get("ACQ")
        parsed_data["condizione_giuridica"]["indicazione_generica"] = dettaglio_map_flat.get("ACQI")
        parsed_data["condizione_giuridica"]["indirizzo"] = dettaglio_map_flat.get("ACQA")

        parsed_data["compilazione"]["data"] = dettaglio_map_flat.get("CMPD")
        parsed_data["compilazione"]["nome_compilatore"] = dettaglio_map_flat.get("CMPN")

        # --- Logica di Aggregazione per Modelli Correlati (LISTE) ---
        i = 0
        temp_misura = {}
        scavo_data = {}
        START_BLOCK_CODES = ["BIB", "STMA", "ISC", "FTS", "MISZ", "DSCV"]
        
        while i < len(dettaglio):
            item = dettaglio[i]
            codice_campo = item.get("codiceCampo")
            valore_campo = item.get("valore")

            # --- Misure (MISZ, MISU, MISM, MISV) ---
            if codice_campo == "MISZ":
                # Se c'era una misura precedente incompleta, la salviamo
                if temp_misura and temp_misura.get('tipo'):
                    parsed_data["misure_dettagliate"].append(temp_misura)
                
                # Inizializza una nuova misura
                temp_misura = {'tipo': valore_campo, 'valore': None, 'unita': None, 'varie': None}
            elif codice_campo == "MISM" and temp_misura:
                valore_pulito = str(valore_campo).replace(',', '.').replace('(max)', '').strip()
                try:
                    temp_misura['valore'] = float(valore_pulito)
                except (ValueError, TypeError):
                    temp_misura['valore'] = None
            elif codice_campo == "MISU" and temp_misura:
                temp_misura['unita'] = valore_campo
            elif codice_campo == "MISV" and temp_misura:
                temp_misura['varie'] = valore_campo
            
            # --- Scavo Archeologico (DSCV, DSCD, DSCA, DSCN) ---
            elif codice_campo == "DSCV":
                if scavo_data: # Se c'è un blocco scavo precedente, lo salviamo
                    parsed_data["scavi"].append(scavo_data)
                
                # Inizializza un nuovo scavo
                scavo_data = {"denominazione": valore_campo}
            elif codice_campo == "DSCD" and scavo_data:
                scavo_data["data_inizio_scavo"] = valore_campo
            elif codice_campo == "DSCA" and scavo_data:
                scavo_data["area_scavo"] = valore_campo
            elif codice_campo == "DSCN" and scavo_data:
                scavo_data["denominazione_area"] = valore_campo

            # --- Blocchi Ripetibili esistenti (Bibliografia, Stemma, Iscrizione, Doc. Fotografica) ---
            # La logica per questi blocchi è mantenuta (BIB, STMA, ISC, FTS) ma ora deve includere i nuovi codici di blocco come interruttori
            
            # [*** Logica per Bibliografia, Stemma, Iscrizione, Doc. Fotografica mantenuta ***]
            # Assicurati che i nuovi blocchi (MISZ, DSCV) siano inclusi nel controllo del ciclo interno
            
            if codice_campo == "BIB":
                # ... (Logica per BIB/BIBA/BIBE/BIBC/BIBCmp) ...
                biblio_data = {"genere": item.get("valore")}
                j = i + 1
                while j < len(dettaglio) and dettaglio[j].get("codiceCampo") not in START_BLOCK_CODES:
                    sub_codice = dettaglio[j].get("codiceCampo")
                    sub_valore = dettaglio[j].get("valore")
                    if sub_codice == "BIBA": biblio_data["autore"] = sub_valore
                    elif sub_codice == "BIBE": biblio_data["anno_edizione"] = sub_valore
                    elif sub_codice == "BIBC": biblio_data["sigla_citazione"] = sub_valore
                    elif sub_codice == "BIBCmp": biblio_data["citazione_completa"] = sub_valore
                    j += 1
                parsed_data["bibliografia"].append(biblio_data)
                i = j - 1
            
            elif codice_campo == "STMA":
                # ... (Logica per STMA/STMQ/STMP/STMD) ...
                stemma_data = {"classe_appartenenza": item.get("valore")}
                j = i + 1
                while j < len(dettaglio) and dettaglio[j].get("codiceCampo") not in START_BLOCK_CODES:
                    sub_codice = dettaglio[j].get("codiceCampo")
                    sub_valore = dettaglio[j].get("valore")
                    if sub_codice == "STMQ": stemma_data["quantita"] = sub_valore
                    elif sub_codice == "STMP": stemma_data["posizione"] = sub_valore
                    elif sub_codice == "STMD": stemma_data["descrizione"] = sub_valore
                    j += 1
                parsed_data["stemmi"].append(stemma_data)
                i = j - 1

            elif codice_campo == "ISC":
                # ... (Logica per ISC/ISCL/ISCT/ISCH/ISCP/ISCTr) ...
                iscrizione_data = {"classe_appartenenza": item.get("valore")}
                j = i + 1
                while j < len(dettaglio) and dettaglio[j].get("codiceCampo") not in START_BLOCK_CODES:
                    sub_codice = dettaglio[j].get("codiceCampo")
                    sub_valore = dettaglio[j].get("valore")
                    if sub_codice == "ISCL": iscrizione_data["lingua"] = sub_valore
                    elif sub_codice == "ISCT": iscrizione_data["tecnica_scrittura"] = sub_valore
                    elif sub_codice == "ISCH": iscrizione_data["tipo_caratteri"] = sub_valore
                    elif sub_codice == "ISCP": iscrizione_data["posizione"] = sub_valore
                    elif sub_codice == "ISCTr": iscrizione_data["trascrizione"] = sub_valore
                    j += 1
                parsed_data["iscrizioni"].append(iscrizione_data)
                i = j - 1
            
            elif codice_campo == "FTS":
                # ... (Logica per FTS/FTT/FTE/FTC) ...
                doc_foto_data = {"genere": item.get("valore")}
                j = i + 1
                while j < len(dettaglio) and dettaglio[j].get("codiceCampo") not in START_BLOCK_CODES:
                    sub_codice = dettaglio[j].get("codiceCampo")
                    sub_valore = dettaglio[j].get("valore")
                    if sub_codice == "FTT": doc_foto_data["tipo"] = sub_valore
                    elif sub_codice == "FTE": doc_foto_data["ente_proprietario"] = sub_valore
                    elif sub_codice == "FTC": doc_foto_data["codice_identificativo"] = sub_valore
                    j += 1
                parsed_data["documentazione_fotografica"].append(doc_foto_data)
                i = j - 1
            
            i += 1
            
        # Aggiunge l'ultima misura e l'ultimo scavo trovati (se esistono)
        if temp_misura and temp_misura.get('tipo'):
            parsed_data["misure_dettagliate"].append(temp_misura)
        if scavo_data:
            parsed_data["scavi"].append(scavo_data)
            
        # --- Immagini (lista, non solo la prima) ---
        for img_data in immagini_raw:
            parsed_data["immagini"].append({
                'url_large': img_data.get("imageLarge"),
                'url_thumbnail': img_data.get("thumbnail")
            })
            
        return parsed_data

    def populate_related_models(self, reperto, parsed_data):
        """Popola i modelli correlati (ForeignKey e OneToOne)."""
        
        # 1. Eliminazione Dati Vecchi e Creazione (Molti a Uno)
        # Rimuoviamo i vecchi dati correlati prima di inserire i nuovi (approccio "fresco")
        reperto.stemmi.all().delete()
        reperto.iscrizioni.all().delete()
        reperto.bibliografia.all().delete()
        reperto.documentazione_fotografica.all().delete()
        
        # NUOVO: Elimina vecchie Immagini, Misure e Scavi
        reperto.immagini.all().delete()
        reperto.misure_dettagliate.all().delete() # Assumendo related_name='misure_dettagliate'
        reperto.scavi.all().delete()

        # Creazione dati esistenti
        for stemma_data in parsed_data["stemmi"]:
            Stemma.objects.create(reperto=reperto, **stemma_data)
        
        for iscrizione_data in parsed_data["iscrizioni"]:
            Iscrizione.objects.create(reperto=reperto, **iscrizione_data)

        for bibliografia_data in parsed_data["bibliografia"]:
            Bibliografia.objects.create(reperto=reperto, **bibliografia_data)
        
        for doc_foto_data in parsed_data["documentazione_fotografica"]:
            DocumentazioneFotografica.objects.create(reperto=reperto, **doc_foto_data)
            
        # NUOVO: Creazione Immagini, Misure e Scavi
        for img_data in parsed_data["immagini"]:
            # Filtriamo se mancano gli URL critici
            if img_data.get('url_large'):
                ImmagineReperto.objects.create(reperto=reperto, **img_data)

        for misura_data in parsed_data["misure_dettagliate"]:
            # Creiamo solo se ci sono dati significativi
            if misura_data.get('tipo') or misura_data.get('valore') is not None:
                 Misura.objects.create(reperto=reperto, **misura_data)

        for scavo_data in parsed_data["scavi"]:
            if scavo_data.get('denominazione'):
                ScavoArcheologico.objects.create(reperto=reperto, **scavo_data)

        # 2. Update or Create OneToOne
        if parsed_data["condizione_giuridica"]:
            CondizioneGiuridica.objects.update_or_create(
                reperto=reperto,
                defaults=parsed_data["condizione_giuridica"]
            )
        
        if parsed_data["compilazione"]:
            Compilazione.objects.update_or_create(
                reperto=reperto,
                defaults=parsed_data["compilazione"]
            )


    def handle(self, *args, **kwargs):
        empty_count = 0
        success_count = 0

        self.stdout.write(self.style.NOTICE(f"Avvio l'importazione dei reperti {PREFIX}1. Interruzione dinamica dopo {MAX_EMPTY_CONSECUTIVE} reperti vuoti consecutivi."))

        for i in range(1, MAX_ID_CHECK + 1):
            codice = f"{PREFIX}{i}"
            params = {"requestField": "nrInv", "requestValue": codice}

            try:
                # 1. Richiesta dati
                r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
                r.raise_for_status()
                data = r.json()

                # 2. Parsing e Validazione (gestisce KeyError e JSON vuoto)
                parsed_data = self.parse_json_data(data)

                # --- LOGICA DI INTERRUZIONE E CONTEGGIO NULLI ---
                if parsed_data is None:
                    empty_count += 1
                    self.stdout.write(self.style.WARNING(f"[{codice}] Dati non trovati/JSON non valido (Vuoti: {empty_count}/{MAX_EMPTY_CONSECUTIVE})"))
                    
                    if empty_count >= MAX_EMPTY_CONSECUTIVE:
                        self.stdout.write(self.style.SUCCESS(f"Raggiunto limite di {MAX_EMPTY_CONSECUTIVE} reperti vuoti consecutivi. INTERRUZIONE IMPORT."))
                        break
                    time.sleep(0.2)
                    continue
                # --- FINE LOGICA DI INTERRUZIONE ---

                # Reset del contatore se il reperto è valido
                empty_count = 0
                
                # --- Logica di Salvataggio in Database ---
                with transaction.atomic():
                    reperto_data = parsed_data.pop("reperto_main")
                    codice_chiave = reperto_data.get("codice_inventario_patrimoniale")
                    
                    if not codice_chiave:
                        self.stdout.write(self.style.ERROR(f"[{codice}] Salto: Codice di inventario INPC non trovato nei dati."))
                        continue
                        
                    # 1. Aggiorna o Crea il Reperto Principale (usa INPC come chiave)
                    reperto, created = Reperto.objects.update_or_create(
                        codice_inventario_patrimoniale=codice_chiave,
                        defaults=reperto_data
                    )
                    
                    # 2. Popola i modelli correlati (ForeignKey e OneToOne)
                    self.populate_related_models(reperto, parsed_data)
                    
                    success_count += 1
                    action = "CREATO" if created else "AGGIORNATO"
                    self.stdout.write(self.style.SUCCESS(f"[{codice_chiave}] Importato e {action}."))

                time.sleep(0.5)

            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"[{codice}] Errore Richiesta HTTP/Connessione: {e}"))
                time.sleep(2)
            except Exception as e:
                # Questo catcha errori DB, errori di parsing imprevisti, ecc.
                self.stdout.write(self.style.ERROR(f"[{codice}] Errore generico (Rollback DB): {e}"))
                time.sleep(2)
            
        self.stdout.write(self.style.NOTICE(f"\n--- IMPORTAZIONE COMPLETATA ---"))
        self.stdout.write(self.style.SUCCESS(f"Reperti importati con successo: {success_count}"))