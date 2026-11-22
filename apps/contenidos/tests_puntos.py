"""Pruebas de los puntos oficiales de la SDA (RF-12) con una respuesta simulada del servicio."""
import io
import json
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.core import pruebas as P

from .models import FuentePunto, PuntoEntrega


def feature(gid, nombre, lon, lat, residuos, localidad='Suba', telefono='No registra'):
    return {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
            'properties': {'gid': gid, 'nombre': nombre, 'direccion': 'KR 92 147C 02', 'horario': 'L - V: 8:00 am - 5:00 pm',
                           'localidad_nombre': localidad, 'sectorcatastral_nombre': 'Suba Urbano', 'telefono': telefono,
                           'residuo_id': residuos, 'residuo_nombre': 'Pilas o acumuladores', 'fecha': '2026-08-04'}}


class Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def servicio(features):
    cuerpo = json.dumps({'type': 'FeatureCollection', 'features': features,
                         'meta': {'total_count': len(features), 'next': None}}).encode()
    return mock.patch('urllib.request.urlopen', return_value=Respuesta(cuerpo))


class SincronizacionSDATests(TestCase):
    def setUp(self):
        _, self.autor, self.revisor = P.usuarios()
        call_command('cargar_contenido_inicial', autor=self.autor.correo, revisor=self.revisor.correo, demo=True, stdout=io.StringIO())

    def test_carga_puntos_con_coordenadas_y_residuos(self):
        with servicio([feature(1, 'ACUAVARES CLÍNICA VETERINARIA', -74.084513, 4.743257, [9]),
                       feature(2, 'Admicentros S.A.S', -74.127501, 4.648027, [10, 1], localidad='Fontibon')]):
            call_command('sincronizar_puntos_sda', stdout=io.StringIO())
        p = PuntoEntrega.objects.get(fuente=FuentePunto.SDA, id_externo='2')
        self.assertEqual((float(p.latitud), float(p.longitud)), (4.648027, -74.127501))
        self.assertEqual(p.telefono, '', '«No registra» no se muestra como teléfono')
        self.assertEqual(sorted(p.residuos.values_list('nombre', flat=True)), ['Aceite de cocina usado', 'Batería de celular', 'Pilas'])
        self.assertEqual(PuntoEntrega.objects.get(id_externo='1').nombre, 'Acuavares Clínica Veterinaria')
        self.assertFalse(PuntoEntrega.objects.filter(nombre__endswith='(ejemplo)', activo=True).exists())

    def test_es_idempotente_y_desactiva_lo_que_ya_no_publica(self):
        with servicio([feature(1, 'A', -74.08, 4.74, [10]), feature(2, 'B', -74.12, 4.64, [10])]):
            call_command('sincronizar_puntos_sda', stdout=io.StringIO())
        with servicio([feature(1, 'A', -74.08, 4.74, [10])]):
            call_command('sincronizar_puntos_sda', stdout=io.StringIO())
        self.assertEqual(PuntoEntrega.objects.filter(fuente='SDA').count(), 2)
        self.assertFalse(PuntoEntrega.objects.get(id_externo='2').activo)

    def test_descarta_coordenadas_fuera_de_bogota(self):
        with servicio([feature(1, 'Malo', 74.08, -4.74, [10])]):
            call_command('sincronizar_puntos_sda', stdout=io.StringIO())
        self.assertFalse(PuntoEntrega.objects.filter(fuente='SDA').exists())

    def test_mapa_y_datos_json(self):
        with servicio([feature(1, 'Punto Pilas', -74.08, 4.74, [10])]):
            call_command('sincronizar_puntos_sda', stdout=io.StringIO())
        from apps.contenidos.models import Residuo
        pilas = Residuo.objects.get(nombre='Pilas')
        r = self.client.get(f'/puntos/?residuo={pilas.pk}')
        self.assertContains(r, 'Punto Pilas')
        self.assertContains(r, 'Secretaría Distrital de Ambiente')
        self.assertContains(r, 'https://www.google.com/maps/dir/?api=1&amp;destination=4.740000,-74.080000')
        datos = self.client.get(f'/puntos/datos.json?residuo={pilas.pk}').json()['puntos']
        self.assertEqual(datos[0]['n'], 'Punto Pilas')
        self.assertNotIn('ip', json.dumps(datos))

    def test_falla_de_red_no_borra_nada(self):
        with servicio([feature(1, 'A', -74.08, 4.74, [10])]):
            call_command('sincronizar_puntos_sda', stdout=io.StringIO())
        with mock.patch('urllib.request.urlopen', side_effect=OSError('sin red')):
            with self.assertRaises(Exception):
                call_command('sincronizar_puntos_sda', stdout=io.StringIO())
        self.assertTrue(PuntoEntrega.objects.get(id_externo='1').activo)

    def test_permisos_de_camara_y_ubicacion_solo_para_el_sitio(self):
        r = self.client.get('/puntos/')
        self.assertIn('geolocation=(self)', r['Permissions-Policy'])
        self.assertIn('camera=(self)', r['Permissions-Policy'])
        self.assertIn('https://tile.openstreetmap.org', r['Content-Security-Policy'])
