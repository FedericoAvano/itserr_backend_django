from django.contrib import admin
from .models import (
    MyModel, 
    Reperto, 
    Texture, 
    Annotazione,
    Stemma,
    Iscrizione,
    Bibliografia,
    DocumentazioneFotografica,
    CondizioneGiuridica,
    Compilazione,
    # --- NUOVI MODELLI IMPORTATI ---
    ImmagineReperto,
    Misura,
    ScavoArcheologico,
)

# Personalizzazione intestazioni admin
admin.site.site_header = "Gestione Reperti"
admin.site.site_title = "Admin ITSERR"
admin.site.index_title = "Pannello di Controllo"


# =========================================================================
# 1. CLASSI INLINE (Per visualizzare i dati relazionali nella pagina del Reperto)
# =========================================================================

class TextureInline(admin.TabularInline):
    # Relazione con MyModel
    model = Texture
    extra = 1
    fields = ("texture_file",)

class ImmagineRepertoInline(admin.TabularInline):
    # Relazione con Reperto (Dato: immagini multiple)
    model = ImmagineReperto
    extra = 1
    fields = ('url_large', 'url_thumbnail')

class MisuraInline(admin.TabularInline):
    # Relazione con Reperto (Dato: MIS - 1171 reperti)
    model = Misura
    extra = 1
    fields = ('tipo', 'valore', 'unita', 'varie')
    ordering = ('tipo',)

class ScavoArcheologicoInline(admin.TabularInline):
    # Relazione con Reperto (Dato: DSC)
    model = ScavoArcheologico
    extra = 1
    fields = ('denominazione', 'responsabile_scientifico', 'riferimento_cronologico')

class BibliografiaInline(admin.TabularInline):
    # Relazione con Reperto (Dato: BIBR)
    model = Bibliografia
    extra = 1
    fields = ('citazione_completa',)
    verbose_name_plural = "Bibliografia (BIBR)"

class DocumentazioneFotograficaInline(admin.TabularInline):
    # Relazione con Reperto (Dato: FTA/FTAS/FTAN)
    model = DocumentazioneFotografica
    extra = 1
    fields = ('uso_foto', 'codice_identificativo')
    verbose_name_plural = "Documentazione Fotografica (FTA)"

class StemmaInline(admin.TabularInline):
    model = Stemma
    extra = 1

class IscrizioneInline(admin.TabularInline):
    model = Iscrizione
    extra = 1

# =========================================================================
# 2. MODELLI PRINCIPALI
# =========================================================================

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name", "reperto__codice")
    inlines = [TextureInline]


@admin.register(Reperto)
class RepertoAdmin(admin.ModelAdmin):
    list_display = (
        'codice',
        'definizione',
        'tipologia_funzionale', # Nuovo campo OGT
        'categoria_materiale',
        'riferimento_cronologico',
        'mymodel',
    )
    list_filter = (
        'categoria_materiale',
        'classe_produzione',
        'riferimento_cronologico',
    )
    search_fields = (
        'codice',
        'definizione',
        'descrizione',
        'specifiche_collocazione', # Nuovo campo LDCS
    )
    list_per_page = 20
    
    fieldsets = (
        (None, {
            'fields': ('codice', 'mymodel', 'definizione', 'tipologia_funzionale', 'descrizione', 'notizie_storico_critiche')
        }),
        ('Dati Tecnici e Cronologici', {
            'fields': ('categoria_materiale', 'classe_produzione', 'materia_tecnica', 'riferimento_cronologico')
        }),
        ('Inventario e Conservazione', {
            'fields': ('nome_inventario', 'codice_inventario_patrimoniale', 'data_inventario', 'provenienza', 'stato_conservazione')
        }),
        ('Localizzazione', {
            'fields': ('regione', 'provincia', 'comune', 'denominazione_museo', 'indirizzo', 'denominazione_raccolta', 'sezione', 'specifiche_collocazione')
        }),
        ('Reperimento', {
            'fields': ('specifiche_reperimento',)
        }),
    )

    # Includi tutti i dati correlati come tabelle secondarie
    inlines = [
        ImmagineRepertoInline,
        MisuraInline,
        ScavoArcheologicoInline,
        BibliografiaInline,
        DocumentazioneFotograficaInline,
        StemmaInline,
        IscrizioneInline,
    ]


# =========================================================================
# 3. REGISTRAZIONI AGGIUNTIVE
# =========================================================================

# Registra i modelli che non sono Inlined
@admin.register(Texture)
class TextureAdmin(admin.ModelAdmin):
    list_display = ("id", "modello", "texture_file")
    search_fields = ("modello__name",) 

@admin.register(Annotazione)
class AnnotazioneAdmin(admin.ModelAdmin):
    list_display = ("id", "categoria", "testo", "modello", "creato_il")
    list_filter = ("categoria", "creato_il")
    search_fields = ("testo", "modello__name") 

# Registra i modelli OneToOne (non possono essere TabularInline)
admin.site.register(CondizioneGiuridica)
admin.site.register(Compilazione)

# Rimuoviamo la registrazione dei modelli che ora sono Inlined, a meno che non si voglia una pagina separata
# admin.site.register(Stemma)
# admin.site.register(Iscrizione)
# admin.site.register(Bibliografia)
# admin.site.register(DocumentazioneFotografica)
admin.site.register(ImmagineReperto) # Mantieniamo la registrazione per l'accesso diretto
admin.site.register(Misura)
admin.site.register(ScavoArcheologico)