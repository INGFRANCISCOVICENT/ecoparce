"""
Punto de entrada WSGI. En PythonAnywhere el archivo WSGI del panel Web
debe agregar la ruta del proyecto e importar `application` desde aquí.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.produccion')
application = get_wsgi_application()
