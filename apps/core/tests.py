from django.test import TestCase

from apps.core.texto import normalizar


class NormalizarTests(TestCase):
    def test_quita_tildes_mayusculas_y_signos(self):
        self.assertEqual(normalizar('  Cáscara  de PLÁTANO! '), 'cascara de platano')

    def test_vacio(self):
        self.assertEqual(normalizar(None), '')


class PaginasPublicasTests(TestCase):
    def test_paginas_responden(self):
        for url in ['/', '/guias/', '/manejo/', '/buscar/', '/trivia/', '/privacidad/', '/terminos/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_cabeceras_de_seguridad(self):
        r = self.client.get('/')
        self.assertIn("frame-ancestors 'none'", r['Content-Security-Policy'])
        self.assertEqual(r['X-Frame-Options'], 'DENY')
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')

    def test_404_personalizado(self):
        r = self.client.get('/no-existe/')
        self.assertEqual(r.status_code, 404)

    def test_robots_txt(self):
        r = self.client.get('/robots.txt')
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/plain', r['Content-Type'])
        self.assertIn('Disallow: /panel/', r.content.decode())
        self.assertIn('Sitemap:', r.content.decode())

    def test_sitemap_xml_respeta_rn01(self):
        from apps.contenidos.models import EstadoContenido, Guia, TipoGuia
        from apps.cuentas.models import Rol, Usuario
        autor = Usuario.objects.create_user('autor_sm@ejemplo.co', 'Autor', 'ClaveSegura123!', rol=Rol.CONTENIDO)
        revisor = Usuario.objects.create_user('revisor_sm@ejemplo.co', 'Revisor', 'ClaveSegura123!', rol=Rol.CONTENIDO)
        Guia.objects.create(
            titulo='Guía pública', slug='guia-publica', tipo=TipoGuia.MANEJO,
            resumen='Resumen', cuerpo='Cuerpo', fuente_oficial='MinAmbiente',
            estado=EstadoContenido.PUBLICADO, autor=autor, revisor=revisor,
        )
        Guia.objects.create(
            titulo='Guía borrador', slug='guia-borrador', tipo=TipoGuia.MANEJO,
            resumen='Resumen', cuerpo='Cuerpo', fuente_oficial='MinAmbiente',
            estado=EstadoContenido.BORRADOR, autor=autor,
        )
        r = self.client.get('/sitemap.xml')
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/xml', r['Content-Type'])
        xml = r.content.decode()
        self.assertIn('/guias/guia-publica/', xml)
        self.assertNotIn('/guias/guia-borrador/', xml)

    def test_metadatos_pwa_y_accesibilidad(self):
        r = self.client.get('/')
        html = r.content.decode()
        self.assertIn('manifest.webmanifest', html)
        self.assertIn('rel="canonical"', html)
        self.assertIn('aria-current="page"', html)
        self.assertIn('id="banner-cookies"', html)
        self.assertIn('id="btn-contraste"', html)

    def test_paginas_legales_y_transparencia(self):
        r_priv = self.client.get('/privacidad/')
        self.assertEqual(r_priv.status_code, 200)
        self.assertContains(r_priv, 'fjnv1305@gmail.com')
        self.assertContains(r_priv, '24 meses')
        r_term = self.client.get('/terminos/')
        self.assertEqual(r_term.status_code, 200)
        self.assertContains(r_term, 'fjnv1305@gmail.com')
        r_lic = self.client.get('/licencias/')
        self.assertEqual(r_lic.status_code, 200)
        self.assertContains(r_lic, 'SIL Open Font License 1.1')
        self.assertContains(r_lic, 'auditoria-sdks')
