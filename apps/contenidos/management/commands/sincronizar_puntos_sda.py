"""Sincroniza los puntos de recolección posconsumo OFICIALES de Bogotá.

Fuente: Secretaría Distrital de Ambiente, Visor Geográfico Ambiental
(https://visorgeo.ambientebogota.gov.co/, servicio /api/v1/posconsumo_vista/). Licencia de los datos abiertos
de la SDA: Creative Commons Atribución 4.0. Se cita la fuente en cada punto.

    python manage.py sincronizar_puntos_sda                # descarga desde el servicio oficial
    python manage.py sincronizar_puntos_sda --archivo x.geojson   # usa un GeoJSON descargado del visor

Es idempotente. Los puntos que la SDA ya no publica quedan inactivos (no se borran).
Programar una vez por semana en PythonAnywhere (Tasks).
"""
import json
import urllib.request
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.contenidos import datos_iniciales as D
from apps.contenidos.models import FuentePunto, PuntoEntrega, Residuo

URL_SDA = 'https://visorgeo.ambientebogota.gov.co/api/v1/posconsumo_vista/?format=geojson&limit={limite}&offset={offset}'
# Límites de Bogotá para descartar coordenadas erradas
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = Decimal('3.7'), Decimal('4.9'), Decimal('-74.5'), Decimal('-73.9')


def descargar(limite=500, timeout=30):
    offset, features = 0, []
    while True:
        url = URL_SDA.format(limite=limite, offset=offset)
        req = urllib.request.Request(url, headers={'User-Agent': f'EcoParce/1.2 (+{settings.SITE_URL}; {settings.CONTACTO_SEGURIDAD})',
                                                   'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310: URL fija https del servicio oficial
            datos = json.loads(r.read().decode('utf-8'))
        features += datos.get('features', [])
        meta = datos.get('meta', {})
        offset += limite
        if not meta.get('next') or offset >= meta.get('total_count', 0):
            return features


def limpiar(texto, largo):
    texto = ' '.join(str(texto or '').split())
    return '' if texto.lower() in ('no registra', 'n/a', 'na', '-') else texto[:largo]


class Command(BaseCommand):
    help = 'Carga o actualiza los puntos posconsumo oficiales de la Secretaría Distrital de Ambiente de Bogotá.'

    def add_arguments(self, parser):
        parser.add_argument('--archivo', help='GeoJSON descargado del Visor Geográfico Ambiental (opcional).')
        parser.add_argument('--si-vacio', action='store_true', help='Solo sincroniza si aún no hay puntos oficiales.')

    def handle(self, *args, **o):
        if o['si_vacio'] and PuntoEntrega.objects.filter(fuente=FuentePunto.SDA).exists():
            self.stdout.write('Ya hay puntos oficiales cargados.')
            return
        try:
            if o['archivo']:
                with open(o['archivo'], encoding='utf-8') as f:
                    features = json.load(f).get('features', [])
            else:
                features = descargar()
        except Exception as e:  # red caída, servicio cambiado, archivo dañado
            raise CommandError(f'No se pudo obtener la información de la SDA: {e}') from e
        if not features:
            raise CommandError('La fuente no devolvió puntos; no se modificó nada.')
        self._guardar(features)

    @transaction.atomic
    def _guardar(self, features):
        residuos = {r.nombre: r for r in Residuo.objects.filter(es_especial=True)}
        vistos, creados, actualizados, descartados = set(), 0, 0, 0
        for f in features:
            p = f.get('properties') or {}
            coords = (f.get('geometry') or {}).get('coordinates') or p.get('coordinates') or []
            gid = str(p.get('gid') or '').strip()
            if not gid or len(coords) != 2:
                descartados += 1
                continue
            lon, lat = (Decimal(str(round(float(c), 6))) for c in coords)
            if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
                descartados += 1
                continue
            try:
                fecha = date.fromisoformat(str(p.get('fecha'))[:10])
            except ValueError:
                fecha = None
            punto, nuevo = PuntoEntrega.objects.update_or_create(fuente=FuentePunto.SDA, id_externo=gid, defaults={
                'nombre': limpiar(p.get('nombre'), 160).title() if str(p.get('nombre', '')).isupper() else limpiar(p.get('nombre'), 160),
                'direccion': limpiar(p.get('direccion'), 160) or 'Sin dirección registrada',
                'localidad': limpiar(p.get('localidad_nombre'), 60) or 'Bogotá',
                'barrio': limpiar(p.get('sectorcatastral_nombre'), 80),
                'horario': limpiar(p.get('horario'), 200) or 'Consultar horario en el punto',
                'telefono': limpiar(p.get('telefono'), 40),
                'latitud': lat, 'longitud': lon,
                'recibe': limpiar(p.get('residuo_nombre'), 300),
                'verificado_en': fecha, 'activo': True})
            nombres = {n for i in (p.get('residuo_id') or []) for n in D.SDA_A_ECOPARCE.get(int(i), [])}
            punto.residuos.set([residuos[n] for n in nombres if n in residuos])
            vistos.add(punto.pk)
            creados += nuevo
            actualizados += not nuevo
        retirados = PuntoEntrega.objects.filter(fuente=FuentePunto.SDA, activo=True).exclude(pk__in=vistos).update(activo=False)
        # Con datos oficiales cargados, los puntos de ejemplo dejan de mostrarse
        PuntoEntrega.objects.filter(fuente=FuentePunto.MANUAL, nombre__endswith='(ejemplo)').update(activo=False)
        self.stdout.write(self.style.SUCCESS(
            f'Puntos oficiales SDA: {creados} nuevos, {actualizados} actualizados, {retirados} ya no publicados, '
            f'{descartados} descartados por datos incompletos.'))
