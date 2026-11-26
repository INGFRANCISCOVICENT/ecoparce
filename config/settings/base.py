"""
Configuración común de EcoParce (Django 5.2 LTS).
Los valores sensibles se leen de variables de entorno (archivo .env en desarrollo).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / '.env')


def env(nombre, defecto=None):
    return os.environ.get(nombre, defecto)


SECRET_KEY = env('DJANGO_SECRET_KEY', 'clave-solo-para-desarrollo-cambiar-en-produccion')
DEBUG = False
ALLOWED_HOSTS = []
SITE_URL = env('SITE_URL', 'http://127.0.0.1:8000')

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.mfa',
    'apps.core',
    'apps.cuentas',
    'apps.auditoria',
    'apps.contenidos',
    'apps.buscador',
    'apps.qr',
    'apps.trivia',
    'apps.estadisticas',
    'apps.api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'apps.api.gateway.ApiGatewayMiddleware',            # API Gateway (WAF, API Key, rate limit, bitácora)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.rls.RLSContextMiddleware',               # contexto Row-Level Security por petición
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'apps.core.middleware.CabecerasSeguridadMiddleware',
    'apps.cuentas.middleware.ControlAccesoMiddleware',  # consentimiento, MFA del panel e inactividad
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'apps.core.context_processors.sitio',
    ]},
}]

# Base de datos: MySQL 8.0 en producción. En desarrollo se puede usar SQLite
# definiendo DB_ENGINE=sqlite en el archivo .env.
if env('DB_ENGINE', 'mysql') == 'sqlite':
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
else:
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME', 'ecoparce'),
        'USER': env('DB_USER', 'root'),
        'PASSWORD': env('DB_PASSWORD', ''),
        'HOST': env('DB_HOST', '127.0.0.1'),
        'PORT': env('DB_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4', 'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"},
        'CONN_MAX_AGE': 280,  # PythonAnywhere cierra conexiones inactivas a los 300 s
    }}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# MySQL no admite restricciones únicas parciales (allauth las usa en EmailAddress y Authenticator).
# La unicidad real queda garantizada por usuario.correo UNIQUE y por las validaciones de allauth.
SILENCED_SYSTEM_CHECKS = ['models.W036']
AUTH_USER_MODEL = 'cuentas.Usuario'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 9}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'apps.cuentas.validadores.ClaveSeguraValidator'},
]

LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = '/'          # el adaptador decide: panel para administradores, «Mi cuenta» para visitantes
LOGOUT_REDIRECT_URL = '/'

# Contraseñas (solo existen para el acceso de emergencia en desarrollo): Argon2id como algoritmo principal
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]

# ---------------------------------------------------------------------------
# Inicio de sesión con Google (OpenID Connect) mediante django-allauth
# ---------------------------------------------------------------------------
ACCOUNT_ADAPTER = 'apps.cuentas.adaptadores.CuentaAdapter'
SOCIALACCOUNT_ADAPTER = 'apps.cuentas.adaptadores.GoogleAdapter'
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = 'correo'
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_FORMS = {'login': 'apps.cuentas.forms.IngresoForm'}
ACCOUNT_SIGNUP_FORM_CLASS = 'apps.cuentas.forms.RegistroForm'   # nombre + autorizaciones (Ley 1581)
# Verificación de correo por código: en producción es obligatoria; en local se activa con VERIFICAR_CORREO_POR_CODIGO=1.
_VERIFICAR_CORREO_POR_CODIGO = env('VERIFICAR_CORREO_POR_CODIGO', '0') == '1'
ACCOUNT_EMAIL_VERIFICATION = 'mandatory' if _VERIFICAR_CORREO_POR_CODIGO else 'optional'
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = _VERIFICAR_CORREO_POR_CODIGO
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT = 15 * 60
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS = 5
ACCOUNT_PASSWORD_RESET_BY_CODE_ENABLED = True       # recuperar contraseña con código, no con enlaces largos
ACCOUNT_PASSWORD_RESET_BY_CODE_TIMEOUT = 15 * 60
ACCOUNT_PASSWORD_RESET_BY_CODE_MAX_ATTEMPTS = 5
ACCOUNT_LOGIN_ON_PASSWORD_RESET = False
ACCOUNT_EMAIL_NOTIFICATIONS = True                  # alerta por correo al cambiar contraseña, activar 2FA, etc.
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[EcoParce] '
ACCOUNT_CHANGE_EMAIL = False
ACCOUNT_MAX_EMAIL_ADDRESSES = 1
ACCOUNT_PASSWORD_MIN_LENGTH = 9
VERIFICAR_MX_CORREO = env('VERIFICAR_MX_CORREO', '1') == '1'   # el dominio del correo debe recibir email
ACCOUNT_SESSION_REMEMBER = False           # la sesión termina al cerrar el navegador
ACCOUNT_LOGOUT_ON_GET = False              # cerrar sesión solo por POST (evita CSRF de cierre)
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_REAUTHENTICATION_TIMEOUT = 300     # acciones sensibles exigen haber verificado identidad hace < 5 min
ACCOUNT_RATE_LIMITS = {
    'login': '20/m/ip',
    'login_failed': '5/5m/ip,5/15m/key',
    'reauthenticate': '5/m/user',
    'signup': '10/h/ip',
    'confirm_email': '1/3m/key',
    'reset_password': '20/m/ip,5/m/key',  # nosec B105 (es un límite de frecuencia, no una contraseña)
    'reset_password_from_key': '20/m/ip',  # nosec B105
}
SOCIALACCOUNT_LOGIN_ON_GET = False         # el inicio con Google se dispara solo con POST + token CSRF
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_STORE_TOKENS = False         # no se guardan tokens de Google: solo el identificador «sub»
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # un administrador creado por correo se enlaza a su Google verificado
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_REQUESTS_TIMEOUT = 10
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APPS': [{'client_id': env('GOOGLE_CLIENT_ID', ''), 'secret': env('GOOGLE_CLIENT_SECRET', ''), 'key': ''}],
        'SCOPE': ['openid', 'email', 'profile'],
        'AUTH_PARAMS': {'access_type': 'online', 'prompt': 'select_account'},
        'OAUTH_PKCE_ENABLED': True,        # PKCE (RFC 7636) además del parámetro «state»
        'FETCH_USERINFO': False,
    },
}

# Verificación en dos pasos (TOTP, compatible con Google Authenticator, Microsoft Authenticator, Authy...)
MFA_ADAPTER = 'apps.cuentas.mfa_adapter.MFAAdapter'
MFA_CLAVES_CIFRADO = [k for k in [env('MFA_CLAVE_CIFRADO', ''), env('MFA_CLAVE_CIFRADO_ANTERIOR', '')] if k]
DB_CLAVES_CIFRADO = [k for k in [env('DB_CLAVE_CIFRADO', ''), env('DB_CLAVE_CIFRADO_ANTERIOR', '')] if k]
MFA_SUPPORTED_TYPES = ['totp', 'recovery_codes']
MFA_TOTP_ISSUER = 'EcoParce'
MFA_TOTP_TOLERANCE = 1
MFA_RECOVERY_CODE_COUNT = 10
MFA_TRUST_ENABLED = False                  # no se ofrece «recordar este navegador» para el panel

# Reglas propias de acceso
PANEL_SOLO_GOOGLE = env('PANEL_SOLO_GOOGLE', '0') == '1'   # si se activa, el panel exige haber entrado con Google
EXIGIR_MFA_PANEL = True
PANEL_INACTIVIDAD_SEGUNDOS = 30 * 60
VERSION_AVISO_PRIVACIDAD = '2026-11'
IP_CABECERA_CONFIABLE = None
CONTACTO_SEGURIDAD = env('CONTACTO_SEGURIDAD', 'seguridad@ecoparce.com.co')   # en producción: HTTP_X_REAL_IP

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True  # se guarda en UTC y se muestra en hora de Colombia

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

SESSION_COOKIE_AGE = 60 * 60 * 8          # 8 horas como máximo absoluto
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_621_440     # 2.5 MB máximo por petición (anti-DoS)
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440
DATA_UPLOAD_MAX_NUMBER_FIELDS = 500
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Caché compartida entre procesos (límites de intentos de allauth y de EcoParce)
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.db.DatabaseCache', 'LOCATION': 'cache_ecoparce'}}

# Correo transaccional (códigos de verificación y alertas de seguridad).
# Funciona con Resend (smtp.resend.com, usuario «resend», contraseña = API key) o Gmail con contraseña de aplicación.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('SMTP_HOST', '')
EMAIL_PORT = int(env('SMTP_PORT', '465'))
EMAIL_USE_SSL = env('SMTP_SSL', '1') == '1'
EMAIL_USE_TLS = not EMAIL_USE_SSL and env('SMTP_TLS', '1') == '1'
EMAIL_HOST_USER = env('SMTP_USER', '')
EMAIL_HOST_PASSWORD = env('SMTP_PASSWORD', '')
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = env('CORREO_REMITENTE', 'EcoParce <no-responder@ecoparce.com.co>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Parámetros de negocio
TRIVIA_PREGUNTAS_POR_PARTIDA = 5
SUGERENCIAS_MAX_POR_HORA = 5
ESCANEO_VENTANA_SEGUNDOS = 600   # una misma persona que relee el QR en 10 minutos no infla las estadísticas
RETENCION_USO_MESES = 24

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'consola': {'class': 'logging.StreamHandler'}},
    'loggers': {'django': {'handlers': ['consola'], 'level': 'WARNING'},
                'ecoparce': {'handlers': ['consola'], 'level': 'INFO'}},
}
