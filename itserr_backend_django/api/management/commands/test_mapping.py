import requests
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Analisi diagnostica completa di tutti i campi INV1.0 su tutti i reperti."

    BASE_URL = "https://museoscerrato.unior.it/restSipor/rest/json/fun/visualizzaScheda"
    PREFIX = "MO"
    MAX_ID = 9999

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("--- Avvio Diagnostica INV1.0 ---"))
        
        # Mappatura basata sul PDF INV1.0
        campi_inv = {
            'TSK': 'Tipo modulo', 'CDM': 'Codice modulo', 'CBT': 'Tipo scheda catalogo',
            'OGD': 'Definizione', 'OGT': 'Tipologia', 'CTG': 'Categoria', 'CLP': 'Classe prod.',
            'PVCS': 'Stato', 'PVCR': 'Regione', 'PVCP': 'Provincia', 'PVCC': 'Comune',
            'LDCN': 'Museo', 'LDCU': 'Indirizzo', 'LDCS': 'Collocazione', 'LDCZ': 'Sezione',
            'DES': 'Descrizione', 'NSC': 'Notizie storiche', 'MTC': 'Materia tecnica',
            'STCC': 'Stato conservazione', 'FTAS': 'Uso foto', 'FTAN': 'ID foto',
            'BIBR': 'Biblio', 'INPO': 'Nome inventario', 'INPC': 'Codice inv.', 'INPD': 'Data inv.'
        }

        report = {
            "totale_analizzati": 0,
            "totale_trovati": 0,
            "totale_mancanti": 0,
            "errori_campi": {codice: 0 for codice in campi_inv.keys()}
        }

        for i in range(1, self.MAX_ID + 1):
            codice = f"{self.PREFIX}{i}"
            report["totale_analizzati"] += 1
            
            # Feedback ogni 100 per non perdere il controllo
            if i % 100 == 0:
                self.stdout.write(f"Scansione in corso... ultimo reperto: {codice}")

            try:
                r = requests.get(self.BASE_URL, params={"requestField": "nrInv", "requestValue": codice}, timeout=5)
                
                if r.status_code != 200:
                    report["totale_mancanti"] += 1
                    continue
                
                json_data = r.json()
                dettaglio = json_data.get('jsonData', {}).get('dettaglio', [])
                
                if not dettaglio:
                    continue

                report["totale_trovati"] += 1
                dettaglio_map = {item.get("codiceCampo"): item.get("valore") for item in dettaglio}

                # Controllo se i campi della scheda INV1.0 sono popolati
                for codice_campo in campi_inv.keys():
                    valore = dettaglio_map.get(codice_campo)
                    if not valore or str(valore).strip() == "":
                        report["errori_campi"][codice_campo] += 1

            except Exception as e:
                continue

        # --- OUTPUT REPORT FINALE ---
        self.stdout.write("\n" + "="*50)
        self.stdout.write("REPORT FINALE DI DIAGNOSTICA INV1.0")
        self.stdout.write("="*50)
        self.stdout.write(f"Totale tentativi: {report['totale_analizzati']}")
        self.stdout.write(f"Reperti trovati su SIPOR: {report['totale_trovati']}")
        self.stdout.write(f"Reperti non esistenti (404): {report['totale_mancanti']}")
        self.stdout.write("\nStatistiche campi mancanti o vuoti:")
        
        for codice, count in report["errori_campi"].items():
            if count > 0:
                self.stdout.write(f" - {campi_inv[codice].ljust(20)} ({codice}): {count} reperti vuoti")
        
        self.stdout.write("="*50)
        self.stdout.write("Procedura completata.")