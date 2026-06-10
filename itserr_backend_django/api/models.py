from django.db import models
from django.utils.text import slugify
import os


# =========================================================================
# FUNZIONI DI SUPPORTO PER L'ORGANIZZAZIONE DEI FILE
# =========================================================================
def path_modelli_3d(instance, filename):
    if isinstance(instance, MyModel):
        folder_name = slugify(instance.name)
    elif hasattr(instance, 'modello'):
        folder_name = slugify(instance.modello.name)
    else:
        folder_name = "generico"
    return os.path.join('modelli_3d', folder_name, filename)


def path_immagini_reperto(instance, filename):
    if instance.reperto and instance.reperto.codice:
        folder_name = slugify(instance.reperto.codice)
    elif instance.reperto:
        folder_name = f"reperto_{instance.reperto.id}"
    else:
        folder_name = "generico"
    return os.path.join('immagini_reperti', folder_name, filename)


# =========================================================================
# 1. MODELLO 3D (MyModel)
# =========================================================================
class MyModel(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nome")
    description = models.TextField(blank=True, verbose_name="Descrizione")
    obj_file = models.FileField(upload_to=path_modelli_3d, max_length=512, verbose_name="File OBJ (Locale)")
    mtl_file = models.FileField(upload_to=path_modelli_3d, max_length=512, verbose_name="File MTL (Locale)", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data di creazione")

    class Meta:
        verbose_name_plural = "Modelli"

    def __str__(self):
        return self.name


# =========================================================================
# 2. MODELLI SIPOR (REPERTO E CORRELATI)
# =========================================================================
class Reperto(models.Model):
    codice = models.CharField(max_length=50, unique=True, blank=True, null=True)
    definizione = models.CharField(max_length=255, blank=True, null=True)
    categoria_materiale = models.CharField(max_length=255, blank=True, null=True)
    classe_produzione = models.CharField(max_length=255, blank=True, null=True)
    tipologia_funzionale = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipologia Funzionale")
    
    regione = models.CharField(max_length=255, blank=True, null=True)
    provincia = models.CharField(max_length=255, blank=True, null=True)
    comune = models.CharField(max_length=255, blank=True, null=True)
    
    denominazione_museo = models.CharField(max_length=255, blank=True, null=True)
    indirizzo = models.CharField(max_length=255, blank=True, null=True)
    denominazione_raccolta = models.CharField(max_length=255, blank=True, null=True)
    sezione = models.CharField(max_length=255, blank=True, null=True)
    specifiche_collocazione = models.CharField(max_length=500, blank=True, null=True, verbose_name="Specifiche Collocazione")
    
    descrizione = models.TextField(blank=True, null=True)
    materia_tecnica = models.CharField(max_length=255, blank=True, null=True)
    riferimento_cronologico = models.CharField(max_length=255, blank=True, null=True)
    specifiche_reperimento = models.CharField(max_length=255, blank=True, null=True)
    
    nome_inventario = models.CharField(max_length=255, blank=True, null=True)
    codice_inventario_patrimoniale = models.CharField(max_length=50, blank=True, null=True)
    data_inventario = models.CharField(max_length=50, blank=True, null=True)
    
    stato_conservazione = models.CharField(max_length=255, blank=True, null=True, verbose_name="Stato di Conservazione")
    notizie_storico_critiche = models.TextField(blank=True, null=True, verbose_name="Notizie Storico-Critiche")
    provenienza = models.CharField(max_length=255, blank=True, null=True, verbose_name="Provenienza")
    
    mymodel = models.ForeignKey("MyModel", on_delete=models.SET_NULL, related_name="reperti", verbose_name="Modello 3D Associato", null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Reperti"
        
    def __str__(self):
        return self.codice or f"Reperto {self.pk}"


class ImmagineReperto(models.Model):
    reperto = models.ForeignKey(Reperto, on_delete=models.CASCADE, related_name="immagini")
    file_immagine = models.ImageField(upload_to=path_immagini_reperto, max_length=1024, verbose_name="File Immagine Locale", blank=True, null=True)
    url_large = models.URLField(max_length=2000, verbose_name="URL Immagine Esterna (Grande)", blank=True, null=True)
    url_thumbnail = models.URLField(max_length=2000, verbose_name="URL Miniatura Esterna", blank=True, null=True)
    didascalia = models.CharField(max_length=255, blank=True, null=True, verbose_name="Didascalia / Tipo Vista")

    class Meta:
        verbose_name_plural = "Immagini Reperti"

    def __str__(self):
        prefix = self.reperto.codice if self.reperto else "Senza Reperto"
        return f"Immagine ({self.pk}) per Reperto: {prefix} - {self.didascalia or 'Senza didascalia'}"

    @property
    def dynamic_url(self):
        """Ritorna il file locale se esiste, altrimenti l'URL remoto."""
        return self.file_immagine.url if self.file_immagine else self.url_large

    @property
    def dynamic_thumbnail_url(self):
        """Ritorna la miniatura locale o remota, con fallback sull'immagine grande."""
        if self.file_immagine:
            return self.file_immagine.url
        return self.url_thumbnail or self.url_large


class Misura(models.Model):
    reperto = models.ForeignKey(Reperto, on_delete=models.CASCADE, related_name="misure_dettagliate")
    tipo = models.CharField(max_length=100, blank=True, null=True)
    valore = models.CharField(max_length=50, blank=True, null=True)
    unita = models.CharField(max_length=15, blank=True, null=True)
    varie = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Misure"


class ScavoArcheologico(models.Model):
    reperto = models.ForeignKey(Reperto, on_delete=models.CASCADE, related_name="scavi")
    denominazione = models.CharField(max_length=250, blank=True, null=True)
    riferimento_cronologico = models.CharField(max_length=100, blank=True, null=True)
    responsabile_scientifico = models.CharField(max_length=250, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Scavi Archeologici"


class Stemma(models.Model):
    reperto = models.ForeignKey(Reperto, on_delete=models.CASCADE, related_name="stemmi", null=True, blank=True)
    classe_appartenenza = models.CharField(max_length=255, blank=True, null=True)
    quantita = models.IntegerField(blank=True, null=True)
    posizione = models.CharField(max_length=255, blank=True, null=True)
    descrizione = models.TextField(blank=True, null=True)


class Iscrizione(models.Model):
    reperto = models.ForeignKey(Reperto, on_delete=models.CASCADE, related_name="iscrizioni", null=True, blank=True)
    classe_appartenenza = models.CharField(max_length=255, blank=True, null=True)
    lingua = models.CharField(max_length=50, blank=True, null=True)
    tecnica_scrittura = models.CharField(max_length=255, blank=True, null=True)
    tipo_caratteri = models.CharField(max_length=255, blank=True, null=True)
    posizione = models.CharField(max_length=255, blank=True, null=True)
    trascrizione = models.TextField(blank=True, null=True)


class Bibliografia(models.Model):
    reperto = models.ForeignKey(Reperto, on_delete=models.CASCADE, related_name="bibliografia", null=True, blank=True)
    citazione_completa = models.TextField(blank=True, null=True)


class DocumentazioneFotografica(models.Model):
    reperto = models.ForeignKey(Reperto, on_delete=models.CASCADE, related_name="documentazione_fotografica", null=True, blank=True)
    uso_foto = models.CharField(max_length=100, blank=True, null=True)
    codice_identificativo = models.CharField(max_length=50, blank=True, null=True)


class CondizioneGiuridica(models.Model):
    reperto = models.OneToOneField(Reperto, on_delete=models.CASCADE, primary_key=True, related_name='condizione_giuridica')
    tipo_acquisizione = models.CharField(max_length=255, blank=True, null=True)
    nome = models.CharField(max_length=255, blank=True, null=True)


class Compilazione(models.Model):
    reperto = models.OneToOneField(Reperto, on_delete=models.CASCADE, primary_key=True, related_name='compilazione')
    data = models.CharField(max_length=50, blank=True, null=True)
    nome_compilatore = models.CharField(max_length=255, blank=True, null=True)


# =========================================================================
# 3. TEXTURE E ASSET 3D
# =========================================================================
class Texture(models.Model):
    modello = models.ForeignKey(MyModel, on_delete=models.CASCADE, related_name="textures")
    texture_file = models.ImageField(upload_to=path_modelli_3d, verbose_name="File Immagine Texture", null=True, blank=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Textures"
    
    def __str__(self):
        return f"Texture per {self.modello.name}"


# =========================================================================
# 4. MODELLI IA (NLP E SNAPPING)
# =========================================================================
class ArcheoConcept(models.Model):
    CONCEPT_TYPES = [('punto', 'Punto'), ('area', 'Area'), ('linea', 'Linea')]
    name = models.CharField(max_length=255, unique=True)
    source = models.CharField(max_length=50, default="AAT/ICCD")
    keywords_text = models.TextField()
    embedding_vector = models.JSONField()
    expected_3d_type = models.CharField(max_length=10, choices=CONCEPT_TYPES, default='punto')

    class Meta:
        verbose_name_plural = "Concetti Archeologici (IA)"

    def __str__(self):
        return self.name


class ModelPOI(models.Model):
    modello = models.ForeignKey(MyModel, on_delete=models.CASCADE, related_name="feature_pois")
    points_json = models.JSONField(verbose_name="Coordinate Punti Salienti")
    concept = models.ForeignKey(ArcheoConcept, on_delete=models.SET_NULL, null=True, blank=True)
    source_algorithm = models.CharField(max_length=100)
    
    class Meta:
        verbose_name_plural = "Punti di Interesse 3D"
        unique_together = ('modello', 'source_algorithm')


# =========================================================================
# 5. ANNOTAZIONI
# =========================================================================
class Annotazione(models.Model):
    CATEGORIE = [
        ("misura", "Misura"), ("materiale", "Materiale"), ("danno", "Danno"),
        ("restauro", "Restauro"), ("descrizione", "Descrizione"),
    ]

    modello = models.ForeignKey("MyModel", on_delete=models.CASCADE, related_name="annotazioni", null=True, blank=True)
    autore_nome = models.CharField(max_length=100, blank=True, null=True)
    autore_cognome = models.CharField(max_length=100, blank=True, null=True)
    testo = models.TextField()
    categoria = models.CharField(max_length=20, choices=CATEGORIE, default="descrizione")
    
    posizione_x = models.FloatField(null=True, blank=True)
    posizione_y = models.FloatField(null=True, blank=True)
    posizione_z = models.FloatField(null=True, blank=True)
    
    target_geometry_json = models.JSONField(null=True, blank=True)
    creato_il = models.DateTimeField(auto_now_add=True)
    analisi_ia_json = models.JSONField(null=True, blank=True, default=dict)

    class Meta:
        verbose_name_plural = "Annotazioni"

    def __str__(self):
        prefix = self.modello.name if self.modello else "Senza Modello"
        return f"{self.categoria} su {prefix}"