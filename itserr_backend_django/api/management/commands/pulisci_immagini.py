from django.core.management.base import BaseCommand
from django.db.models import Count
from api.models import ImmagineReperto

class Command(BaseCommand):
    help = 'Rimuove i duplicati delle immagini nel database'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- Inizio scansione duplicati ---")
        
        # Identifica i gruppi duplicati basati su reperto e url_large
        duplicati = ImmagineReperto.objects.values('reperto', 'url_large').annotate(
            conteggio=Count('id')
        ).filter(conteggio__gt=1)

        if not duplicati.exists():
            self.stdout.write(self.style.SUCCESS("Nessun duplicato trovato."))
            return

        totale_rimosse = 0

        for dup in duplicati:
            reperto_id = dup['reperto']
            url = dup['url_large']
            
            # Recupera tutte le istanze, ordinando per ID
            immagini_identiche = ImmagineReperto.objects.filter(
                reperto_id=reperto_id, 
                url_large=url
            ).order_by('id')
            
            # Convertiamo in lista per mantenere solo la prima istanza
            lista_img = list(immagini_identiche)
            da_eliminare = lista_img[1:]
            
            for img in da_eliminare:
                self.stdout.write(f"Eliminazione ID: {img.id} | Reperto: {reperto_id}")
                img.delete()
                totale_rimosse += 1

        self.stdout.write(self.style.SUCCESS(f"--- Operazione completata. Totale record eliminati: {totale_rimosse} ---"))