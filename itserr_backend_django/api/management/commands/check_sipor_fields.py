import requests
import pprint
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurazione
URL = "https://museoscerrato.unior.it/restSipor/rest/json/fun/visualizzaScheda"
PARAMS = {'requestField': 'nrInv', 'requestValue': 'MO15'}

# Chiamata API
response = requests.get(URL, params=PARAMS, timeout=15, verify=False)
data = response.json()

# Estrazione dati
if not data.get('messageBean', {}).get('error', True):
    dettaglio = data.get('jsonData', {}).get('dettaglio', [])
    immagini = data.get('jsonData', {}).get('immagini', [])
    
    # Stampa formattata dei dati
    print(f"\n--- REPERTO: MO15 ---")
    for campo in dettaglio:
        if campo.get('valore'):
            print(f"{campo['descrizione']:<35} : {campo['valore']}")
    
    if immagini:
        print(f"\n--- IMMAGINI TROVATE ({len(immagini)}) ---")
        pprint.pprint(immagini)
    else:
        print("\n--- NESSUNA IMMAGINE ASSOCIATA ---")
else:
    print("Errore: API non raggiungibile o reperto non trovato.")