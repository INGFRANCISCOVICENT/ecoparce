"""Pruebas del escáner de productos (RF-16) con respuestas simuladas de Open Food Facts."""
from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from .escaner import analizar, clasificar_material

GASEOSA = {'product_name': 'Gaseosa 400 ml', 'brands': 'Marca X', 'packagings': [
    {'material': 'en:pet-1-polyethylene-terephthalate', 'shape': 'en:bottle'},
    {'material': 'en:plastic', 'shape': 'en:bottle-cap'},
    {'material': 'en:paper', 'shape': 'en:label'}]}
PAPAS = {'product_name': 'Papas fritas', 'packagings': [{'material': 'en:metallised-plastic', 'shape': 'en:bag'}]}
LECHE = {'product_name': 'Leche', 'packaging_tags': ['en:tetra-pak', 'en:brick']}
PILAS = {'product_name': 'Pilas AA', 'categories_tags': ['en:batteries']}


class EscanerTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_clasificacion_por_material(self):
        self.assertEqual(clasificar_material('en:glass')[0], 'BLANCA')
        self.assertEqual(clasificar_material('en:aluminium')[0], 'BLANCA')
        self.assertEqual(clasificar_material('en:metallised-plastic')[0], 'NEGRA')
        self.assertIsNone(clasificar_material('en:unknown'))

    def test_gaseosa_por_partes(self):
        partes = analizar(GASEOSA)
        self.assertEqual({(p['parte'], p['codigo']) for p in partes},
                         {('Botella', 'BLANCA'), ('Etiqueta', 'BLANCA')})

    def test_paquete_metalizado_va_en_negra(self):
        self.assertEqual(analizar(PAPAS)[0]['codigo'], 'NEGRA')

    def test_tetrapak_por_etiquetas(self):
        self.assertEqual(analizar(LECHE)[0]['codigo'], 'BLANCA')

    def test_pilas_van_a_posconsumo(self):
        self.assertEqual(analizar(PILAS)[0]['codigo'], 'POSCONSUMO')

    def test_endpoint(self):
        with mock.patch('apps.buscador.escaner._consultar', return_value=GASEOSA):
            r = self.client.get('/escanear/producto/7702004003508/')
        datos = r.json()
        self.assertTrue(datos['encontrado'])
        self.assertEqual(datos['nombre'], 'Gaseosa 400 ml')
        self.assertEqual(datos['fuente'], 'Open Food Facts')

    def test_codigo_invalido_no_consulta_afuera(self):
        with mock.patch('apps.buscador.escaner._consultar') as m:
            r = self.client.get('/escanear/producto/12ab/')
        self.assertEqual(r.status_code, 400)
        m.assert_not_called()

    def test_no_encontrado_y_cache(self):
        with mock.patch('apps.buscador.escaner._consultar', return_value=None) as m:
            self.assertFalse(self.client.get('/escanear/producto/0000000000000/').json()['encontrado'])
            self.client.get('/escanear/producto/0000000000000/')
        from apps.buscador.escaner import BASES
        self.assertEqual(m.call_count, len(BASES), 'se consulta una vez en cada base y luego se usa la caché')

    def test_red_caida_responde_sin_error_500(self):
        with mock.patch('apps.buscador.escaner._consultar', side_effect=OSError('sin red')):
            r = self.client.get('/escanear/producto/7702004003508/')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()['encontrado'])

    def test_pagina_escanear(self):
        r = self.client.get('/escanear/')
        self.assertContains(r, 'Tomar foto del producto')
        self.assertContains(r, '/escanear/foto/')

    def test_analizar_foto_producto_local_y_seleccion_material(self):
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        # 1. Foto JPEG válida sin clave IA: no adivina por color (identificado=False)
        buf = io.BytesIO()
        Image.new('RGB', (120, 120), color=(40, 180, 70)).save(buf, format='JPEG')
        foto = SimpleUploadedFile('objeto.jpg', buf.getvalue(), content_type='image/jpeg')
        r = self.client.post('/escanear/foto/', {'foto': foto})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d['ok'])
        self.assertFalse(d['identificado'])
        self.assertEqual(d['metodo'], 'requiere_ia_o_seleccion')

        # 2. Ajuste directo en 1 toque -> electrónico (PC/RAEE) va a POSCONSUMO con puntos_url
        r2 = self.client.post('/escanear/foto/', {'tipo': 'electronico'})
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json()['identificado'])
        self.assertEqual(r2.json()['codigo'], 'POSCONSUMO')
        self.assertTrue(r2.json().get('puntos_url'))

        # 3. Archivo corrupto rechazado con 400
        malo = SimpleUploadedFile('malo.jpg', b'no-es-una-imagen', content_type='image/jpeg')
        self.assertEqual(self.client.post('/escanear/foto/', {'foto': malo}).status_code, 400)

    def test_upcitemdb_e_inferencia_inteligente_de_empaque(self):
        fake_upc = {
            'product_name_es': 'Papas Margarita Pollo 105g',
            'brands': 'Margarita',
            'packaging_tags': [],
            'categories_tags': ['Snacks'],
        }
        with mock.patch('apps.buscador.escaner._consultar', return_value=None), \
             mock.patch('apps.buscador.escaner._consultar_upcitemdb', return_value=fake_upc):
            r = self.client.get('/escanear/producto/7702189000123/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d['encontrado'])
        self.assertEqual(d['fuente'], 'UPCitemdb Global')
        self.assertEqual(d['partes'][0]['codigo'], 'NEGRA')

    def test_asistente_eco_conversacional_y_reglas_expertas(self):
        # Saludo profesional
        r_hola = self.client.get('/asistente/consultar/?q=hola')
        self.assertEqual(r_hola.status_code, 200)
        self.assertTrue(r_hola.json()['encontrado'])

        # Caja de pizza con grasa -> Bolsa Negra
        r_pizza = self.client.get('/asistente/consultar/?q=donde boto una caja de pizza con grasa')
        self.assertEqual(r_pizza.status_code, 200)
        self.assertEqual(r_pizza.json()['codigo'], 'NEGRA')

        # Computador -> Posconsumo RAEE
        r_pc = self.client.get('/asistente/consultar/?q=donde boto un computador viejo')
        self.assertEqual(r_pc.status_code, 200)
        self.assertEqual(r_pc.json()['codigo'], 'POSCONSUMO')
        self.assertTrue(r_pc.json().get('puntos_url'))

    def test_google_sin_configurar_no_manda_a_google(self):
        from django.test import override_settings
        with override_settings(SOCIALACCOUNT_PROVIDERS={'google': {'APPS': [{'client_id': '', 'secret': '', 'key': ''}]}}):
            r = self.client.post('/accounts/google/login/')
        self.assertRedirects(r, '/accounts/login/')
