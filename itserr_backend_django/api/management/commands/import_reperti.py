import requests
import json
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import (
    Reperto, Stemma, Iscrizione, Bibliografia, DocumentazioneFotografica,
    CondizioneGiuridica, Compilazione, ImmagineReperto, Misura, ScavoArcheologico,
)

# --- Configurazione ---
BASE_URL = "https://museoscerrato.unior.it/restSipor/rest/json/fun/visualizzaScheda"
PREFIX = "MO"
MAX_ID_CHECK = 1251 # Numero di reperti reali identificati
HEADERS = {'accept': 'application/json'}

class Command(BaseCommand):
    help = "Sincronizzazione coerente e pulita dei reperti dal server SIPOR."

    def parse_json_data(self, data):
        dettaglio = data.get('jsonData', {}).get('dettaglio', [])
        immagini_raw = data.get('jsonData', {}).get('immagini', [])
        
        dettaglio_map_flat = {item.get("codiceCampo"): item.get("valore") for item in dettaglio}
        
        parsed_data = {
            "reperto_main": {},
            "stemmi": [], "iscrizioni": [], "bibliografia": [],
            "documentazione_fotografica": [], "condizione_giuridica": {},
            "compilazione": {}, "immagini": [], "misure_dettagliate": [], "scavi": [],
        }
        
        # Mapping campi principali (solo quelli che abbiamo confermato esistenti)
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
            "OGT": "tipologia_funzionale", "LDCS": "specifiche_collocazione",
            "STCC": "stato_conservazione", "NSC": "notizie_storico_critiche",
            "INPP": "provenienza"
        }
        
        for codice, field in mapping_main.items():
            val = dettaglio_map_flat.get(codice)
            if val and str(val).strip():
                parsed_data["reperto_main"][field] = val
        
        parsed_data["reperto_main"]["codice"] = dettaglio_map_flat.get("INPC")
        
        # Gestione blocchi complessi e ripetuti
        i = 0
        temp_misura = {}
        scavo_data = {}
        START_BLOCK_CODES = ["BIB", "STMA", "ISC", "FTS", "MISZ", "DSCV"]
        
        while i < len(dettaglio):
            item = dettaglio[i]
            codice, valore = item.get("codiceCampo"), item.get("valore")

            if codice == "MISZ":
                if temp_misura and temp_misura.get('tipo'): parsed_data["misure_dettagliate"].append(temp_misura)
                temp_misura = {'tipo': valore, 'valore': None, 'unita': None}
            elif codice == "MISM" and temp_misura:
                val_p = str(valore).replace(',', '.').split('(')[0].strip()
                try: temp_misura['valore'] = float(val_p)
                except: temp_misura['valore'] = None
            elif codice == "MISU" and temp_misura: temp_misura['unita'] = valore
            
            elif codice == "DSCV":
                if scavo_data: parsed_data["scavi"].append(scavo_data)
                scavo_data = {"denominazione": valore}
            elif codice == "DSCA" and scavo_data: scavo_data["area_scavo"] = valore
            
            elif codice == "BIB" and valore:
                parsed_data["bibliografia"].append({"citazione_completa": valore})
            
            # (Segui la logica precedente per Stemmi/Iscrizioni/Foto...)
            i += 1
            
        if temp_misura and temp_misura.get('tipo'): parsed_data["misure_dettagliate"].append(temp_misura)
        
        for img in immagini_raw:
            url = img.get("imageLarge") or img.get("thumbnail")
            if url: parsed_data["immagini"].append({"url_temporaneo": url})
            
        return parsed_data

    def populate_related_models(self, reperto, parsed_data):
        # Pulizia record esistenti
        reperto.stemmi.all().delete()
        reperto.iscrizioni.all().delete()
        reperto.bibliografia.all().delete()
        reperto.misure_dettagliate.all().delete()
        
        # Salvataggio condizionale (solo se i dati esistono)
        for b in parsed_data["bibliografia"]:
            if b.get("citazione_completa"): Bibliografia.objects.create(reperto=reperto, **b)
        
        for m in parsed_data["misure_dettagliate"]:
            if m.get('tipo') or m.get('valore') is not None:
                Misura.objects.create(reperto=reperto, **m)
        
        for img in parsed_data["immagini"]:
            ImmagineReperto.objects.create(reperto=reperto, url_large=img['url_temporaneo'], didascalia="Importato da SIPOR")

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Avvio sincronizzazione..."))
        for i in range(1, MAX_ID_CHECK + 1):
            codice = f"{PREFIX}{i}"
            try:
                r = requests.get(BASE_URL, params={"requestField": "nrInv", "requestValue": codice}, headers=HEADERS, timeout=10)
                if r.status_code != 200: continue
                
                parsed = self.parse_json_data(r.json())
                with transaction.atomic():
                    r_main = parsed.pop("reperto_main")
                    reperto, created = Reperto.objects.update_or_create(
                        codice_inventario_patrimoniale=r_main.get("codice_inventario_patrimoniale"), 
                        defaults=r_main
                    )
                    self.populate_related_models(reperto, parsed)
                self.stdout.write(self.style.SUCCESS(f"Sincronizzato {codice}"))
                time.sleep(0.2)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Errore {codice}: {e}"))