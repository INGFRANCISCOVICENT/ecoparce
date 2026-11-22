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
        self.assertEqual(m.call_count, 3, 'se consulta una vez en cada base y luego se usa la caché')

    def test_red_caida_responde_sin_error_500(self):
        with mock.patch('apps.buscador.escaner._consultar', side_effect=OSError('sin red')):
            r = self.client.get('/escanear/producto/7702004003508/')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()['encontrado'])

    def test_pagina_escanear(self):
        self.assertContains(self.client.get('/escanear/'), 'Abrir cámara')

    def test_google_sin_configurar_no_manda_a_google(self):
        from django.test import override_settings
        with override_settings(SOCIALACCOUNT_PROVIDERS={'google': {'APPS': [{'client_id': '', 'secret': '', 'key': ''}]}}):
            r = self.client.post('/accounts/google/login/')
        self.assertRedirects(r, '/accounts/login/')
