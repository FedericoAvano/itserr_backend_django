from django.core.management.base import BaseCommand
from api.models import Reperto, MyModel

class Command(BaseCommand):
    help = "Ripulisce i Reperti con foreign key MyModel non valida"

    def handle(self, *args, **kwargs):
        orfani = Reperto.objects.exclude(mymodel__in=MyModel.objects.all())
        count = orfani.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("✅ Nessun reperto orfano trovato"))
            return

        # Aggiorna i reperti orfani mettendo mymodel = NULL
        orfani.update(mymodel=None)

        self.stdout.write(
            self.style.WARNING(
                f"⚠️ Trovati {count} reperti orfani. Il campo mymodel è stato impostato a NULL."
            )
        )
