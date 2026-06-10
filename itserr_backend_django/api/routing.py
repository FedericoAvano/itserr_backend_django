from django.urls import re_path
from . import consumers  # Si riferisce a `MyModelViewSet` nella stessa cartella

websocket_urlpatterns = [
    re_path(r'ws/models/$', consumers.MyModelConsumer.as_asgi()),
]