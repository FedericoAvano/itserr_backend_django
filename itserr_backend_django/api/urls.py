from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token # ✅ Import fondamentale
from . import views

router = DefaultRouter()

# ✅ Registrazione ViewSets
router.register(r'modelli', views.MyModelViewSet, basename='mymodel') 
router.register(r'reperti', views.RepertoModelViewSet, basename='reperto')
router.register(r'annotazioni', views.AnnotazioneViewSet, basename='annotation') 
router.register(r'w3c/annotazioni', views.W3CAnnotationViewSet, basename='w3c-annotation') 

# ViewSets SIPOR Correlati
router.register(r'immagini_reperto', views.ImmagineRepertoViewSet)
router.register(r'misure', views.MisuraViewSet)
router.register(r'scavi', views.ScavoArcheologicoViewSet)
router.register(r'stemmi', views.StemmaViewSet)
router.register(r'iscrizioni', views.IscrizioneViewSet)
router.register(r'bibliografie', views.BibliografiaViewSet)
router.register(r'documentazione', views.DocumentazioneFotograficaViewSet)
router.register(r'condizionegiuridica', views.CondizioneGiuridicaViewSet)
router.register(r'compilazione', views.CompilazioneViewSet)
router.register(r'textures', views.TextureViewSet)

urlpatterns = [
    # Router del ViewSet (Include tutte le rotte registrate sopra)
    path('', include(router.urls)),  
    
    # ✅ ENDPOINT LOGIN: Scambia username/password con un Token
    path('login/', obtain_auth_token, name='api_token_auth'),
    
    # Rotta per il proxy SIPOR
    path("proxy/scheda/<str:codice>/", views.proxy_scheda, name="proxy_scheda"),
]

# Servire i file media durante lo sviluppo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)