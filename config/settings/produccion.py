"""
Producción en PythonAnywhere con el dominio www.ecoparce.com.co.
Ajustes de la sección 8.2 del documento técnico. Verificar con:
    python manage.py check --deploy
"""
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import LOGGING, env

DEBUG = False
SECRET_KEY = env('DJANGO_SECRET_KEY')
if not SECRET_KEY or SECRET_KEY.startswith('clave-solo-para'):
    raise ImproperlyConfigured('Defina DJANGO_SECRET_KEY en las variables de entorno de producción.')

ALLOWED_HOSTS = [h.strip() for h in env('ALLOWED_HOSTS', 'www.ecoparce.com.co').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = [f'https://{h}' for h in ALLOWED_HOSTS]
SITE_URL = env('SITE_URL', 'https://www.ecoparce.com.co')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Prefijo __Host-: el navegador solo acepta la cookie por HTTPS, sin atributo Domain y con Path=/
SESSION_COOKIE_NAME = '__Host-sessionid'
CSRF_COOKIE_NAME = '__Host-csrftoken'

# Rotación de la clave secreta sin cerrar todas las sesiones: la anterior va en DJANGO_SECRET_KEY_ANTERIOR
SECRET_KEY_FALLBACKS = [k for k in [env('DJANGO_SECRET_KEY_ANTERIOR', '')] if k]

# IP real del cliente detrás del proxy de PythonAnywhere (para los límites de intentos)
ALLAUTH_TRUSTED_CLIENT_IP_HEADER = 'X-Real-IP'
IP_CABECERA_CONFIABLE = 'HTTP_X_REAL_IP'

for _var, _ayuda in [('GOOGLE_CLIENT_ID', 'Google Auth Platform → Clientes'), ('GOOGLE_CLIENT_SECRET', 'Google Auth Platform → Clientes'),
                     ('MFA_CLAVE_CIFRADO', 'genérela con: python manage.py generar_claves'),
                     ('SMTP_HOST', 'servidor de correo para los códigos de verificación'), ('SMTP_PASSWORD', 'clave del servidor de correo')]:
    if not env(_var):
        raise ImproperlyConfigured(f'Falta la variable de entorno {_var} ({_ayuda}).')

LOGGING['loggers']['ecoparce.seguridad'] = {'handlers': ['consola'], 'level': 'INFO', 'propagate': False}

# La precarga HSTS en los navegadores es irreversible; se activa solo cuando el dominio esté estable.
SILENCED_SYSTEM_CHECKS = ['security.W021', 'models.W036']
