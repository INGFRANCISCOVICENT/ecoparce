"""Desarrollo local: DEBUG activo y sin exigir HTTPS."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']

# En desarrollo los correos (códigos de verificación) se muestran en la consola si no hay SMTP configurado.
if not env('SMTP_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
VERIFICAR_MX_CORREO = env('VERIFICAR_MX_CORREO', '0') == '1'
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
MFA_CLAVE_DERIVADA_DESARROLLO = True  # solo desarrollo: en producción MFA_CLAVE_CIFRADO es obligatoria
