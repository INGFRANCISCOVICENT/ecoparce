"""
Configuración de producción de EcoParce para Render (HTTPS + WhiteNoise + PostgreSQL).
Usa RENDER_EXTERNAL_HOSTNAME y DATABASE_URL automáticamente.
"""
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, LOGGING, MIDDLEWARE, env

DEBUG = False

SECRET_KEY = env('DJANGO_SECRET_KEY')
if not SECRET_KEY or SECRET_KEY.startswith('clave-solo-para'):
    raise ImproperlyConfigured('Defina DJANGO_SECRET_KEY en las variables de entorno de Render.')

RENDER_HOST = env('RENDER_EXTERNAL_HOSTNAME', '').strip()
ALLOWED_HOSTS = [h.strip() for h in env('ALLOWED_HOSTS', '').split(',') if h.strip()]
if RENDER_HOST and RENDER_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOST)
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['.onrender.com']

CSRF_TRUSTED_ORIGINS = [f'https://{h.lstrip(".")}' for h in ALLOWED_HOSTS if not h.startswith('.')]
if RENDER_HOST:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_HOST}')
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))

SITE_URL = env('SITE_URL', f'https://{RENDER_HOST}' if RENDER_HOST else 'https://ecoparce.onrender.com')

# Base de datos: PostgreSQL en Render (DATABASE_URL) con respaldo automático a SQLite si no se define
DATABASE_URL = env('DATABASE_URL', '').strip()
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=300, ssl_require=True),
    }
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

# Archivos estáticos con WhiteNoise (comprimidos y cacheados)
MIDDLEWARE = list(MIDDLEWARE)
if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# Seguridad HTTPS detrás del proxy de Render
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_NAME = '__Host-sessionid'
CSRF_COOKIE_NAME = '__Host-csrftoken'

ALLAUTH_TRUSTED_CLIENT_IP_HEADER = 'X-Forwarded-For'
IP_CABECERA_CONFIABLE = 'HTTP_X_FORWARDED_FOR'

# Si aún no hay SMTP configurado en Render, evitar errores 500 al enviar correos opcionales
if not env('SMTP_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Si aún no se define MFA_CLAVE_CIFRADO, derivar de forma determinística en el primer arranque
if not env('MFA_CLAVE_CIFRADO'):
    MFA_CLAVE_DERIVADA_DESARROLLO = True

VERIFICAR_MX_CORREO = env('VERIFICAR_MX_CORREO', '0') == '1'

LOGGING['loggers']['ecoparce.seguridad'] = {'handlers': ['consola'], 'level': 'INFO', 'propagate': False}
SILENCED_SYSTEM_CHECKS = ['security.W021', 'models.W036']
