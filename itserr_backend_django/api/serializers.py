from rest_framework import serializers
from django.conf import settings
from django.urls import reverse_lazy

from .ai_processor import analizza_testo_annotazione
from .models import (
    Reperto, 
    MyModel, 
    Annotazione, 
    Texture, 
    Stemma, 
    Iscrizione, 
    Bibliografia, 
    DocumentazioneFotografica, 
    CondizioneGiuridica, 
    Compilazione,
    ImmagineReperto,
    Misura,
    ScavoArcheologico
)

# Base URL per i metadati canonici
BASE_URL = getattr(settings, 'BASE_URL', 'http://localhost:8000')

# =========================================================================
# 1. Serializer per Modelli Correlati (Uno-a-Molti)
# =========================================================================

class ImmagineRepertoSerializer(serializers.ModelSerializer):
    # Usiamo le property definite nel model ImmagineReperto
    dynamic_url = serializers.ReadOnlyField()
    dynamic_thumbnail_url = serializers.ReadOnlyField()

    class Meta:
        model = ImmagineReperto
        fields = (
            'id', 
            'reperto', 
            'file_immagine', 
            'url_large', 
            'url_thumbnail', 
            'didascalia',
            'dynamic_url',
            'dynamic_thumbnail_url'
        )
        extra_kwargs = {
            'url_large': {'required': False, 'allow_null': True},
            'url_thumbnail': {'required': False, 'allow_null': True},
            'didascalia': {'required': False, 'allow_null': True},
        }

class MisuraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Misura
        fields = ('id', 'tipo', 'valore', 'unita', 'varie')

class ScavoArcheologicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScavoArcheologico
        fields = '__all__'

class StemmaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stemma
        fields = '__all__'

class IscrizioneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Iscrizione
        fields = '__all__'

class BibliografiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bibliografia
        fields = '__all__'

class DocumentazioneFotograficaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentazioneFotografica
        fields = '__all__'

# =========================================================================
# 2. Serializer per Modelli Correlati (Uno-a-Uno)
# =========================================================================

class CompilazioneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Compilazione
        fields = '__all__'

class CondizioneGiuridicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CondizioneGiuridica
        fields = '__all__'

# =========================================================================
# 3. Serializer Principale: Reperto
# =========================================================================

class RepertoSerializer(serializers.ModelSerializer):
    # 'immagini' è il related_name definito nel modello
    immagini = ImmagineRepertoSerializer(many=True, read_only=True)
    misure_dettagliate = MisuraSerializer(many=True, read_only=True) 
    scavi = ScavoArcheologicoSerializer(many=True, read_only=True)
    stemmi = StemmaSerializer(many=True, read_only=True)
    iscrizioni = IscrizioneSerializer(many=True, read_only=True)
    bibliografia = BibliografiaSerializer(many=True, read_only=True)
    documentazione_fotografica = DocumentazioneFotograficaSerializer(many=True, read_only=True)
    
    condizione_giuridica = CondizioneGiuridicaSerializer(read_only=True)
    compilazione = CompilazioneSerializer(read_only=True) 
    
    class Meta:
        model = Reperto
        fields = "__all__"

# =========================================================================
# 4. Serializer per Modelli 3D e Annessi
# =========================================================================

class AnnotazioneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotazione
        fields = "__all__"
        read_only_fields = ('analisi_ia_json',) 

    def create(self, validated_data):
        testo_da_analizzare = validated_data.get('testo', '')
        analisi_risultati = analizza_testo_annotazione(testo_da_analizzare)
        validated_data['analisi_ia_json'] = analisi_risultati
        return super().create(validated_data)

class TextureSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Texture
        fields = ('id', 'url', 'description')

    def get_url(self, obj):
        if obj.texture_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.texture_file.url)
            return obj.texture_file.url
        return None

class MyModelSerializer(serializers.ModelSerializer):
    textures = TextureSerializer(many=True, read_only=True)
    annotazioni = AnnotazioneSerializer(many=True, read_only=True)
    
    obj_file = serializers.FileField(required=True)
    mtl_file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = MyModel
        fields = [
            'id', 
            'name', 
            'description', 
            'obj_file', 
            'mtl_file', 
            'textures', 
            'created_at',
            'annotazioni',
        ]

# =========================================================================
# 5. Serializer Dublin Core
# =========================================================================

class DublinCoreMyModelSerializer(serializers.ModelSerializer):
    dc_identifier = serializers.CharField(source="id", read_only=True)
    dc_title = serializers.CharField(source="name", read_only=True)
    dc_description = serializers.CharField(source="description", read_only=True)
    dc_date = serializers.DateTimeField(source="created_at", read_only=True)
    dc_source = serializers.SerializerMethodField()

    def get_dc_source(self, obj):
        if obj.obj_file:
            return self.context['request'].build_absolute_uri(obj.obj_file.url)
        return None

    class Meta:
        model = MyModel
        fields = ["dc_identifier", "dc_title", "dc_description", "dc_date", "dc_source"]

# =========================================================================
# 6. Serializer W3C Web Annotation
# =========================================================================

class W3CAnnotationSerializer(serializers.ModelSerializer):
    context = serializers.SerializerMethodField(method_name='get_context_w3c')
    w3c_id = serializers.SerializerMethodField()
    type = serializers.CharField(default="Annotation", read_only=True)
    creator = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    created = serializers.DateTimeField(source='creato_il', read_only=True)
    modified = serializers.DateTimeField(source='creato_il', read_only=True) 

    def get_context_w3c(self, obj):
        return "http://www.w3.org/ns/anno.jsonld"

    def get_w3c_id(self, obj):
        return f"{BASE_URL}/api/annotazioni/{obj.pk}"

    def get_creator(self, obj):
        full_name = f"{obj.autore_nome or ''} {obj.autore_cognome or ''}".strip()
        if not full_name: return None
        return {"type": "Person", "name": full_name}

    def get_body(self, obj):
        bodies = [{
            "type": "TextualBody",
            "value": obj.testo,
            "purpose": "commenting",
            "format": "text/plain"
        }]
        if obj.analisi_ia_json:
            bodies.append({
                "type": "Dataset", 
                "purpose": "tagging",
                "value": obj.analisi_ia_json,
                "format": "application/json"
            })
        return bodies

    def get_target(self, obj):
        model_uri = f"{BASE_URL}/api/modelli/{obj.modello.pk}" if obj.modello else "Unknown"
        return {
            "source": model_uri, 
            "type": "SpecificResource",
            "selector": {
                "type": "FragmentSelector", 
                "value": f"x={obj.posizione_x};y={obj.posizione_y};z={obj.posizione_z}"
            }
        }

    class Meta:
        model = Annotazione
        fields = ('context', 'w3c_id', 'type', 'creator', 'body', 'target', 'created', 'modified')