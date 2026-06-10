import os
import django
import requests


# Configurazione ambiente (Verifica che il nome della cartella sia corretto)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'itserr_backend_django.settings')
django.setup()


from api.models import Reperto, MyModel


def test_github_mo1138():
    # DATI DALLO SCREENSHOT
    USER = "FedericoAvano"
    REPO = "cartelle-modelli"
    BRANCH = "main" 
    CODICE = "MO1138"  # <--- Il codice che vedo nella tua cartella
    
    # Costruzione URL RAW
    base_url = f"https://raw.githubusercontent.com/{USER}/{REPO}/{BRANCH}/{CODICE}"
    url_obj = f"{base_url}/{CODICE}.obj"
    url_mtl = f"{base_url}/{CODICE}.mtl"
    
    print(f"--- TEST COLLEGAMENTO GITHUB ---")
    print(f"Verifico: {url_obj}")
    
    # 1. Test di connessione
    try:
        response = requests.get(url_obj, timeout=10)
        if response.status_code == 200:
            print("✅ SUCCESSO: File OBJ trovato su GitHub!")
            
            # 2. Aggiornamento Database
            # Cerchiamo il reperto o lo creiamo se non esiste
            reperto, created = Reperto.objects.get_or_create(
                codice_inventario_patrimoniale=CODICE,
                defaults={'definizione': 'Reperto 1138'}
            )
            
            # Creiamo il collegamento al modello 3D
            mymodel, _ = MyModel.objects.update_or_create(
                name=f"Modello {CODICE}",
                defaults={
                    'obj_file': url_obj,
                    'mtl_file': url_mtl
                }
            )
            
            reperto.mymodel = mymodel
            reperto.save()
            
            print(f"✅ DATABASE: Reperto {CODICE} collegato al modello 3D.")
        else:
            print(f"❌ ERRORE {response.status_code}: Il file non è stato trovato.")
            print("Verifica che dentro la cartella MO1138 il file si chiami esattamente MO1138.obj")
            
    except Exception as e:
        print(f"❌ ERRORE TECNICO: {e}")


if __name__ == "__main__":
    test_github_mo1138()