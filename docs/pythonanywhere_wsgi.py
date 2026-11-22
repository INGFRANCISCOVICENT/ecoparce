# Contenido para el archivo WSGI de PythonAnywhere (pestaña Web → «WSGI configuration file»).
# Cambie «usuario» por su usuario de PythonAnywhere.
import os
import sys

from dotenv import load_dotenv

RUTA = '/home/usuario/ecoparce'
if RUTA not in sys.path:
    sys.path.insert(0, RUTA)

load_dotenv(os.path.join(RUTA, '.env'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.produccion')

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
