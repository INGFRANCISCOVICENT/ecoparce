from django.test import TestCase

from apps.contenidos.models import EstadoContenido as E
from apps.core import pruebas as P

from .models import ALFABETO, CodigoQR, Escaneo, tipo_dispositivo

IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148'


class QRTests(TestCase):
    def setUp(self):
        self.sistema, self.autor, self.revisor = P.usuarios()
        self.g = P.guia(self.autor, self.revisor)
        self.qr = CodigoQR.objects.create(destino_tipo='GUIA', guia=self.g, ubicacion='Torre 3', creado_por=self.sistema)

    def test_codigo_corto(self):
        self.assertEqual(len(self.qr.codigo_corto), 8)
        self.assertTrue(set(self.qr.codigo_corto) <= set(ALFABETO))

    def test_rf01_redirige_y_registra_escaneo_anonimo(self):
        r = self.client.get(f'/q/{self.qr.codigo_corto}', HTTP_USER_AGENT=IPHONE)
        self.assertRedirects(r, f'{self.g.get_absolute_url()}?qr={self.qr.codigo_corto}')
        e = Escaneo.objects.get()
        self.assertEqual(e.tipo_dispositivo, 'MOVIL')
        self.assertContains(self.client.get(r['Location']), 'Llegaste por un código QR')

    def test_rn06_inactivo_muestra_no_disponible(self):
        self.qr.activo = False
        self.qr.save()
        r = self.client.get(f'/q/{self.qr.codigo_corto}')
        self.assertContains(r, 'Código no disponible', status_code=404)
        self.assertEqual(Escaneo.objects.count(), 0)

    def test_guia_retirada_lleva_al_inicio(self):
        self.g.estado = E.RETIRADO
        self.g.save()
        self.assertRedirects(self.client.get(f'/q/{self.qr.codigo_corto}'), '/')

    def test_rf07_imagenes_png_y_svg(self):
        self.assertTrue(self.qr.generar_imagen('png').startswith(b'\x89PNG'))
        self.assertIn(b'<svg', self.qr.generar_imagen('svg'))
        P.entrar_panel(self.client, self.sistema)
        r = self.client.get(f'/panel/qr/{self.qr.pk}/imagen.svg?descargar=1')
        self.assertEqual(r['Content-Type'], 'image/svg+xml')
        self.assertIn(self.qr.codigo_corto, r['Content-Disposition'])

    def test_crear_y_desactivar_desde_panel(self):
        P.entrar_panel(self.client, self.sistema)
        self.client.post('/panel/qr/', {'destino_tipo': 'TRIVIA', 'ubicacion': 'Salón comunal'})
        nuevo = CodigoQR.objects.get(ubicacion='Salón comunal')
        self.assertIsNone(nuevo.guia)
        self.client.post(f'/panel/qr/{nuevo.pk}/activar/')
        nuevo.refresh_from_db()
        self.assertFalse(nuevo.activo)

    def test_dispositivos(self):
        self.assertEqual(tipo_dispositivo(IPHONE), 'MOVIL')
        self.assertEqual(tipo_dispositivo('Mozilla/5.0 (iPad; CPU OS 17_0)'), 'TABLET')
        self.assertEqual(tipo_dispositivo('Mozilla/5.0 (Linux; Android 14; SM-X200)'), 'TABLET')
        self.assertEqual(tipo_dispositivo('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'), 'ESCRITORIO')
