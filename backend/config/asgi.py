import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
from django.core.asgi import get_asgi_application
django_application=get_asgi_application()
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.conf import settings
from django.urls import path
from core.consumers import SessionConsumer
class AppOriginValidator(OriginValidator):
    def valid_origin(self,origin):
        # Local unpacked extensions get changing IDs. A signed, one-use-duration
        # ticket still authorizes each socket. Production requires an explicit ID.
        import re
        if settings.DEBUG and origin and origin.scheme=='chrome-extension' and re.fullmatch('[a-p]{32}',origin.hostname or ''):
            return True
        return super().valid_origin(origin)
application=ProtocolTypeRouter({'http':django_application,'websocket':AppOriginValidator(URLRouter([path('ws/sessions/<int:pk>/',SessionConsumer.as_asgi())]),settings.CORS_ALLOWED_ORIGINS)})
