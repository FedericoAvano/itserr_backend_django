import os
import zipfile
import io
import re
import requests
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.http import JsonResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser, AllowAny
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend

# Importa i modelli
from .models import (
    MyModel, Reperto, Texture, Annotazione, Stemma, Iscrizione,
    Bibliografia, DocumentazioneFotografica, CondizioneGiuridica,
    Compilazione, ImmagineReperto, Misura, ScavoArcheologico
)

# Importa i serializzatori
from .serializers import (
    MyModelSerializer, RepertoSerializer, TextureSerializer,
    AnnotazioneSerializer, StemmaSerializer, IscrizioneSerializer,
    BibliografiaSerializer, DocumentazioneFotograficaSerializer,
    CondizioneGiuridicaSerializer, CompilazioneSerializer,
    ImmagineRepertoSerializer, MisuraSerializer, ScavoArcheologicoSerializer,
    DublinCoreMyModelSerializer, W3CAnnotationSerializer
)

# Dizionario di mappatura SIPOR
CAMPI_MAPPATI = {
    'OGD': 'definizione', 'OGT': 'tipologia_funzionale', 'CLP': 'classe_produzione',
    'CTG': 'categoria_materiale', 'DES': 'descrizione', 'MTC': 'materia_tecnica',
    'DTR': 'riferimento_cronologico', 'INPO': 'nome_inventario',
    'INPC': 'codice_inventario_patrimoniale', 'INPD': 'data_inventario',
    'INPP': 'provenienza', 'STCC': 'stato_conservazione', 'NSC': 'notizie_storico_critiche',
    'PVCR': 'regione', 'PVCP': 'provincia', 'PVCC': 'comune', 'LDCU': 'indirizzo',
    'LDCM': 'denominazione_raccolta', 'LDCN': 'denominazione_museo', 'LDCZ': 'sezione',
    'LDCS': 'specifiche_collocazione', 'RES': 'specifiche_reperimento',
    'CGS': 'tipo_acquisizione', 'CGN': 'nome_giuridica',
    'CMPN': 'nome_compilatore', 'CMPD': 'data_compilazione',
}


@method_decorator(csrf_exempt, name='dispatch')
class MyModelViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
    
    # Forza la ViewSet a reconocer i metodi di autenticazione standard
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    # Permette GET a tutti, richiede Token per POST/PUT/DELETE
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=["get"], url_path="dublin-core")
    def dublin_core(self, request, pk=None):
        modello = self.get_object()
        serializer = DublinCoreMyModelSerializer(modello, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='clear-annotations', permission_classes=[IsAdminUser])
    def clear_annotations(self, request, pk=None):
        """Rimuove tutti i pin (annotazioni) associati a questo modello"""
        modello = self.get_object()
        deleted_count = Annotazione.objects.filter(modello=modello).delete()
        return Response({"status": f"Cancellate {deleted_count[0]} annotazioni."}, status=status.HTTP_200_OK)

    # 🔴 NOTA: Impostato temporaneamente su AllowAny per catturare i log di debug ed evitare il blocco 401 preventivo
    @action(detail=False, methods=['POST'], url_path='upload-zip', permission_classes=[AllowAny])
    def upload_zip(self, request):
        # 🔴 ------------------ BLOCCO DI DEBUG INIZIO ------------------
        print("\n" + "="*50)
        print("--- DEBUG AUTENTICAZIONE COMPONENTE ZIP ---")
        print("Intestazione Authorization:", request.headers.get('Authorization'))
        print("Metodo della richiesta:", request.method)
        print("Utente istanziato (request.user):", request.user)
        print("L'utente resulta autenticato?:", request.user.is_authenticated)
        print("L'utente ha privilegi Staff/Admin (is_staff)?:", getattr(request.user, 'is_staff', False))
        print("="*50 + "\n")
        # 🔴 ------------------- BLOCCO DI DEBUG FINE -------------------

        zip_file = request.FILES.get('file_zip') or request.FILES.get('file')
        if not zip_file:
            return Response({"error": "Nessun file ZIP fornito"}, status=status.HTTP_400_BAD_REQUEST)

        ALLOWED_EXT = {'.obj', '.mtl', '.jpg', '.jpeg', '.png'}
        IGNORE_LIST = {'__MACOSX', '.DS_STORE', 'THUMBS.DB'}

        try:
            with zipfile.ZipFile(zip_file) as z:
                creati, errori = [], []
                all_paths = z.namelist()
                folders = set()
                
                # --- NUOVO SISTEMA DI FILTRAGGIO E ISOLAMENTO DELLE CARTELLE ---
                for path in all_paths:
                    # Uniforma i separatori di percorso per evitare discrepanze Windows/Mac
                    clean_path = path.replace('\\', '/')
                    parts = [p.strip() for p in clean_path.split('/') if p.strip()]
                    
                    if not parts:
                        continue
                        
                    # Se una qualsiasi parte del percorso appartiene a file nascosti o spazzatura Mac, scarta del tutto
                    if any(p.startswith('.') or p.upper() in IGNORE_LIST for p in parts):
                        continue
                    
                    # La cartella principale è tassativamente il primo blocco del percorso
                    root_folder = parts[0]
                    folders.add(root_folder)

                # --- ELABORAZIONE DELLE CARTELLE PULITE ---
                for folder in folders:
                    try:
                        codice_pulito = folder.strip()
                        rep_esistente = Reperto.objects.filter(codice__iexact=codice_pulito).first()

                        # Filtra solo i file appartenenti a questa specifica cartella, escludendo file di sistema interni
                        valid_files = [
                            f for f in all_paths 
                            if f.replace('\\', '/').startswith(f"{folder}/") and 
                            os.path.splitext(f)[1].lower() in ALLOWED_EXT and
                            not os.path.basename(f).startswith('.') and
                            not any(p.upper() in IGNORE_LIST for p in f.replace('\\', '/').split('/'))
                        ]

                        obj_path = next((f for f in valid_files if f.lower().endswith('.obj')), None)
                        mtl_path = next((f for f in valid_files if f.lower().endswith('.mtl')), None)
                        textures = [f for f in valid_files if f.lower().endswith(('.jpg', '.png', '.jpeg'))]

                        # Se la cartella analizzata non contiene un file .obj strutturale, viene saltata
                        if not obj_path:
                            continue

                        if rep_esistente:
                            nome_modello = rep_esistente.definizione or f"Modello {codice_pulito}"
                            descrizione_modello = rep_esistente.descrizione or f"Modello 3D associato a {codice_pulito}"
                        else:
                            nome_modello = f"Modello {codice_pulito}"
                            descrizione_modello = f"Caricamento automatico da ZIP. Reperto {codice_pulito} non trovato nel DB."

                        modello = MyModel.objects.create(
                            name=nome_modello,
                            description=descrizione_modello
                        )

                        obj_name = os.path.basename(obj_path)
                        modello.obj_file.save(obj_name, ContentFile(z.read(obj_path)), save=False)

                        if mtl_path:
                            try:
                                mtl_content = z.read(mtl_path).decode('utf-8', errors='ignore')
                                new_lines = []
                                for line in mtl_content.splitlines():
                                    if line.strip().lower().startswith(('map_kd', 'map_ks', 'map_bump', 'bump')):
                                        parts_line = line.split()
                                        if len(parts_line) > 1:
                                            tex_name = os.path.basename(parts_line[-1].replace('\\', '/'))
                                            new_lines.append(f"{parts_line[0]} {tex_name}")
                                        else:
                                            new_lines.append(line)
                                    else:
                                        new_lines.append(line)
                                
                                fixed_mtl_data = "\n".join(new_lines).encode('utf-8')
                                mtl_name = os.path.basename(mtl_path)
                                modello.mtl_file.save(mtl_name, ContentFile(fixed_mtl_data), save=False)
                            except Exception:
                                modello.mtl_file.save(os.path.basename(mtl_path), ContentFile(z.read(mtl_path)), save=False)

                        modello.save()

                        for t in textures:
                            tex_filename = os.path.basename(t)
                            Texture.objects.create(
                                modello=modello,
                                texture_file=ContentFile(z.read(t), name=tex_filename)
                            )

                        if rep_esistente:
                            rep_esistente.mymodel = modello
                            rep_esistente.save()
                            creati.append(f"{codice_pulito} (Sincronizzato)")
                        else:
                            creati.append(f"{codice_pulito} (Modello creato, Reperto mancante)")

                    except Exception as e:
                        errori.append(f"Errore {folder}: {str(e)}")

                return Response({"status": "completato", "creati": creati, "errori": errori}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# --- ViewSet Standard con Permessi ---

class TextureViewSet(viewsets.ModelViewSet):
    queryset = Texture.objects.all()
    serializer_class = TextureSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['modello']


class AnnotazioneViewSet(viewsets.ModelViewSet):
    queryset = Annotazione.objects.all().order_by("-creato_il")
    serializer_class = AnnotazioneSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['modello']


class W3CAnnotationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Annotazione.objects.all().order_by("-creato_il")
    serializer_class = W3CAnnotationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['modello']


class RepertoModelViewSet(viewsets.ModelViewSet):
    queryset = Reperto.objects.all()
    serializer_class = RepertoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "codice"


class ImmagineRepertoViewSet(viewsets.ModelViewSet):
    queryset = ImmagineReperto.objects.all()
    serializer_class = ImmagineRepertoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reperto']
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        # Permette di passare 'reperto_codice' (es. MO1234) invece della chiave primaria intera 'reperto'
        codice_reperto = request.data.get('reperto_codice') or request.data.get('reperto')
        
        if codice_reperto and not str(codice_reperto).isdigit():
            reperto_obj = Reperto.objects.filter(codice__iexact=str(codice_reperto).strip()).first()
            if not reperto_obj:
                return Response(
                    {"error": f"Reperto correlato con codice '{codice_reperto}' non trovato nel sistema."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Sostituiamo il valore testuale con l'id relazionale richiesto dal serializer nativo
            data = request.data.copy()
            data['reperto'] = reperto_obj.id
            
            # Applica l'autenticazione/validazione standard
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        return super().create(request, *args, **kwargs)

    # 🛠️ NUOVA ACTION: Upload singolo usando la logica del nome del file (Regex)
    @action(
        detail=False,
        methods=['POST'],
        url_path='upload-single-image',
        permission_classes=[AllowAny],  # Configura IsAuthenticated se preferisci bloccare l'azione in produzione
        parser_classes=[MultiPartParser, FormParser]
    )
    def upload_single_image(self, request):
        """
        Riceve un file immagine singolo (chiave: 'file' o 'immagine'),
        estrapola il codice reperto dal nome (es. 'MO1138 (1).jpg' -> 'MO1138')
        e lo associa al reperto corrispondente.
        """
        file_obj = request.FILES.get('file') or request.FILES.get('immagine')
        if not file_obj:
            return Response({"error": "Nessun file immagine fornito"}, status=status.HTTP_400_BAD_REQUEST)
        
        filename = file_obj.name
        base_name, ext = os.path.splitext(filename)
        base_name = base_name.strip()
        
        # Identica logica Regex collaudata nello ZIP dei modelli e delle coppe
        match = re.match(r'^([A-Za-z0-9]+)(?:\s*\(\d+\))?$', base_name)
        if not match:
            return Response({
                "error": f"Il nome del file '{filename}' non rispetta il formato accettato (es. MO1138.jpg o MO1138 (1).png)"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        codice_reperto = match.group(1).strip()
        
        try:
            reperto_obj = Reperto.objects.filter(codice__iexact=codice_reperto).first()
            if not reperto_obj:
                return Response({
                    "error": f"Reperto '{codice_reperto}' estratto dal file non trovato nel database."
                }, status=status.HTTP_404_NOT_FOUND)
                
            # Creazione effettiva dell'oggetto nel DB
            nuova_immagine = ImmagineReperto.objects.create(
                reperto=reperto_obj,
                file_immagine=file_obj,
                didascalia=f"Caricamento singolo del file {filename}"
            )
            
            return Response({
                "status": "successo",
                "messaggio": f"Immagine associata correttamente al reperto {codice_reperto}",
                "id_immagine": nuova_immagine.id,
                "file_url": nuova_immagine.file_immagine.url
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": f"Errore nel salvataggio: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ✅ CORREZIONE UPLOAD ZIP (Metodo ottimizzato)
    @action(
        detail=False, 
        methods=['POST'], 
        url_path='upload-images-zip', 
        permission_classes=[AllowAny],
        parser_classes=[MultiPartParser, FormParser]
    )
    def upload_images_zip(self, request):
        zip_file = request.FILES.get('file_zip') or request.FILES.get('file')
        if not zip_file:
            return Response({"error": "Nessun file ZIP fornito"}, status=status.HTTP_400_BAD_REQUEST)

        if not zipfile.is_zipfile(zip_file):
            return Response({"error": "Il file fornito non è uno ZIP valido."}, status=status.HTTP_400_BAD_REQUEST)

        ALLOWED_IMG_EXT = {'.jpg', '.jpeg', '.png'}
        IGNORE_LIST = {'__MACOSX', '.DS_STORE', 'THUMBS.DB'}
        
        immagini_create = 0
        errori = []

        try:
            with zipfile.ZipFile(zip_file) as z:
                for file_path in z.namelist():
                    if file_path.endswith('/') or any(ignore in file_path.upper() for ignore in IGNORE_LIST):
                        continue
                    
                    filename = os.path.basename(file_path)
                    if not filename or filename.startswith('.'):
                        continue
                        
                    ext = os.path.splitext(filename)[1].lower()
                    if ext not in ALLOWED_IMG_EXT:
                        continue

                    base_name = os.path.splitext(filename)[0].strip()
                    match = re.match(r'^([A-Za-z0-9]+)(?:\s*\(\d+\))?$', base_name)
                    
                    if not match:
                        errori.append(f"Nome file non conforme ai pattern supportati: {filename}")
                        continue
                    
                    codice_reperto = match.group(1).strip()

                    try:
                        reperto_obj = Reperto.objects.filter(codice__iexact=codice_reperto).first()
                        if not reperto_obj:
                            errori.append(f"Reperto '{codice_reperto}' non trovato nel sistema (File: {filename})")
                            continue
                        
                        file_data = z.read(file_path)
                        django_file = ContentFile(file_data, name=filename)
                        
                        ImmagineReperto.objects.create(
                            reperto=reperto_obj,
                            file_immagine=django_file,
                            didascalia=f"Caricamento massivo ZIP ({filename})"
                        )
                        immagini_create += 1

                    except Exception as e:
                        errori.append(f"Errore durante il salvataggio di {filename}: {str(e)}")

            return Response({
                "status": "completato",
                "immagini_create": immagini_create,
                "errori": errori
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"Errore critico durante l'apertura dello ZIP: {str(e)}"}, status=500)


class MisuraViewSet(viewsets.ModelViewSet):
    queryset = Misura.objects.all()
    serializer_class = MisuraSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reperto']


class ScavoArcheologicoViewSet(viewsets.ModelViewSet):
    queryset = ScavoArcheologico.objects.all()
    serializer_class = ScavoArcheologicoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reperto']


class StemmaViewSet(viewsets.ModelViewSet):
    queryset = Stemma.objects.all()
    serializer_class = StemmaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reperto']


class IscrizioneViewSet(viewsets.ModelViewSet):
    queryset = Iscrizione.objects.all()
    serializer_class = IscrizioneSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reperto']


class BibliografiaViewSet(viewsets.ModelViewSet):
    queryset = Bibliografia.objects.all()
    serializer_class = BibliografiaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reperto']


class DocumentazioneFotograficaViewSet(viewsets.ModelViewSet):
    queryset = DocumentazioneFotografica.objects.all()
    serializer_class = DocumentazioneFotograficaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reperto']


class CondizioneGiuridicaViewSet(viewsets.ModelViewSet):
    queryset = CondizioneGiuridica.objects.all()
    serializer_class = CondizioneGiuridicaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reperto']


class CompilazioneViewSet(viewsets.ModelViewSet):
    queryset = Compilazione.objects.all()
    serializer_class = CompilazioneSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reperto']


@csrf_exempt
def proxy_scheda(request, codice):
    url = f"https://museoscerrato.unior.it/restSipor/rest/json/fun/visualizzaScheda?requestField=nrInv&requestValue={codice}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        reperto_mappato = {}
        dettagli = data.get('jsonData', {}).get('dettaglio', [])
        
        misure_list, bibliografia_list, documentazione_fotografica_list, scavi_list = [], [], [], []
        temp_misura = {}
        
        for item in dettagli:
            cod_c, val_c = item.get('codiceCampo'), item.get('valore')
            if cod_c in CAMPI_MAPPATI:
                reperto_mappato[CAMPI_MAPPATI[cod_c]] = val_c
            elif cod_c in ['MISZ', 'MISM', 'MISU', 'MISV']:
                if cod_c == 'MISZ' and temp_misura:
                    misure_list.append(temp_misura)
                    temp_misura = {}
                if cod_c == 'MISZ': temp_misura['tipo'] = val_c
                elif cod_c == 'MISM': temp_misura['valore'] = val_c
                elif cod_c == 'MISU': temp_misura['unita'] = val_c
                elif cod_c == 'MISV': temp_misura['varie'] = val_c
            elif cod_c == 'BIBR' and val_c:
                bibliografia_list.append({'citazione_completa': val_c})
            elif cod_c == 'FTAS':
                documentazione_fotografica_list.append({'uso_foto': val_c})
            elif cod_c == 'FTAN' and documentazione_fotografica_list:
                documentazione_fotografica_list[-1]['codice_identificativo'] = val_c
            elif cod_c == 'DSCV' and val_c:
                scavi_list.append({'denominazione': val_c})
        
        if temp_misura: misure_list.append(temp_misura)
        
        reperto_mappato.update({
            'misure_dettagliate': misure_list,
            'bibliografia': bibliografia_list,
            'documentazione_fotografica': documentazione_fotografica_list,
            'scavi': scavi_list,
            'condizione_giuridica': {
                'tipo_acquisizione': reperto_mappato.pop('tipo_acquisizione', None),
                'name': reperto_mappato.pop('nome_giuridica', None), 
            },
            'compilazione': {
                'nome_compilatore': reperto_mappato.pop('nome_compilatore', None),
                'data': reperto_mappato.pop('data_compilazione', None)
            }
        })
        
        immagini_raw = data.get('jsonData', {}).get('immagini', [])
        reperto_mappato['immagini'] = [{'url_large': i.get('imageLarge'), 'url_thumbnail': i.get('thumbnail')} for i in immagini_raw]
        
        return JsonResponse(reperto_mappato, safe=False)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)