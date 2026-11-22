"""Borra los registros anónimos de uso más antiguos que RETENCION_USO_MESES (24 por defecto).
Programar mensualmente en PythonAnywhere (Tasks):  python manage.py depurar_registros_uso"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.buscador.models import Busqueda
from apps.qr.models import Escaneo
from apps.trivia.models import PartidaTrivia


class Command(BaseCommand):
    help = 'Aplica la política de retención de datos de uso (aviso de privacidad).'

    def handle(self, *args, **o):
        limite = timezone.now() - timedelta(days=30 * settings.RETENCION_USO_MESES)
        e = Escaneo.objects.filter(fecha_hora__lt=limite).delete()[0]
        b = Busqueda.objects.filter(fecha_hora__lt=limite).delete()[0]
        p = PartidaTrivia.objects.filter(iniciada_en__lt=limite).delete()[0]
        self.stdout.write(self.style.SUCCESS(f'Depurados: {e} escaneos, {b} búsquedas, {p} registros de trivia anteriores a {limite:%Y-%m-%d}.'))
