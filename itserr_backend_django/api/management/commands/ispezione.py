import requests
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Analisi diagnostica mirata sui 1250 reperti esistenti."

    BASE_URL = "https://museoscerrato.unior.it/restSipor/rest/json/fun/visualizzaScheda"
    PREFIX = "MO"
    # Abbiamo scoperto che il range reale è entro i 1250 reperti
    MAX_ID = 1251 

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("--- Avvio Diagnostica Mirata (1250 reperti) ---"))
        
        # Mappatura REALE basata sull'ispezione fatta in precedenza
        campi_reali = {
            'OGD': 'Definizione', 'CTG': 'Categoria', 'CLP': 'Classe prod.',
            'PVCR': 'Regione', 'PVCP': 'Provincia', 'PVCC': 'Comune',
            'LDCN': 'Museo', 'LDCU': 'Indirizzo', 'LDCM': 'Raccolta', 'LDCZ': 'Sezione',
            'DES': 'Descrizione', 'MTC': 'Materia tecnica', 'DTR': 'Cronologia',
            'RES': 'Reperimento', 'INPO': 'Nome inventario', 'INPC': 'Codice inv.', 'INPD': 'Data inv.'
        }

        report = {
            "analizzati": 0,
            "errori_campi": {codice: 0 for codice in campi_reali.keys()}
        }

        for i in range(1, self.MAX_ID + 1):
            codice = f"{self.PREFIX}{i}"
            
            try:
                r = requests.get(self.BASE_URL, params={"requestField": "nrInv", "requestValue": codice}, timeout=5)
                if r.status_code != 200:
                    continue
                
                json_data = r.json()
                dettaglio = json_data.get('jsonData', {}).get('dettaglio', [])
                
                if not dettaglio:
                    continue

                report["analizzati"] += 1
                dettaglio_map = {item.get("codiceCampo"): item.get("valore") for item in dettaglio}

                # Controllo campi reali
                for codice_campo in campi_reali.keys():
                    valore = dettaglio_map.get(codice_campo)
                    if not valore or str(valore).strip() == "":
                        report["errori_campi"][codice_campo] += 1

            except Exception:
                continue

        # --- OUTPUT REPORT FINALE ---
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"REPORT DIAGNOSTICA: Analizzati {report['analizzati']} reperti reali")
        self.stdout.write("="*50)
        
        for codice, count in report["errori_campi"].items():
            perc = (count / report['analizzati']) * 100
            status = "CRITICO" if perc > 50 else "OK"
            self.stdout.write(f" - {campi_reali[codice].ljust(15)} ({codice}): {count} vuoti ({perc:.1f}%)")
        
        self.stdout.write("="*50)
        self.stdout.write("Procedura completata.")