from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.auditoria.models import Accion, RegistroAuditoria
from apps.core import pruebas as P
from apps.qr.models import CodigoQR

from .models import EstadoContenido as E
from .models import Contenedor, Guia


class FlujoRevisionTests(TestCase):
    def setUp(self):
        self.sistema, self.autor, self.revisor = P.usuarios()
        self.g = P.guia(self.autor, estado=E.BORRADOR)

    def test_contenedores_semilla_rn04(self):
        self.assertEqual(list(Contenedor.objects.values_list('codigo', flat=True)), ['BLANCA', 'NEGRA', 'VERDE', 'POSCONSUMO'])

    def test_rn02_fuente_obligatoria(self):
        self.g.fuente_oficial = ' '
        with self.assertRaises(ValidationError):
            self.g.enviar_a_revision(self.autor)

    def test_rn03_autor_no_publica_lo_suyo(self):
        self.g.enviar_a_revision(self.autor)
        with self.assertRaises(PermissionDenied):
            self.g.publicar(self.autor)

    def test_rn03_restriccion_en_base_de_datos(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Guia.objects.filter(pk=self.g.pk).update(revisor=self.autor)

    def test_flujo_completo_con_auditoria(self):
        self.g.enviar_a_revision(self.autor)
        self.g.devolver(self.revisor, 'Falta el artículo')
        self.assertEqual(self.g.estado, E.BORRADOR)
        self.g.enviar_a_revision(self.autor)
        self.g.publicar(self.revisor)
        self.assertEqual(self.g.estado, E.PUBLICADO)
        self.assertIsNotNone(self.g.publicado_en)
        self.g.retirar(self.revisor)
        self.g.reabrir(self.autor)
        self.assertEqual(self.g.estado, E.BORRADOR)
        acciones = list(RegistroAuditoria.objects.filter(entidad='guia', entidad_id=self.g.pk).values_list('accion', flat=True))
        self.assertEqual(sorted(acciones), sorted([Accion.ENVIAR_REVISION, Accion.DEVOLVER, Accion.ENVIAR_REVISION,
                                                   Accion.PUBLICAR, Accion.RETIRAR, Accion.REABRIR]))

    def test_rn01_publico_solo_ve_publicado(self):
        self.assertEqual(self.client.get(self.g.get_absolute_url()).status_code, 404)
        self.g.enviar_a_revision(self.autor)
        self.g.publicar(self.revisor)
        self.assertContains(self.client.get(self.g.get_absolute_url()), 'Bolsa blanca')

    def test_rn10_guia_con_qr_no_se_elimina(self):
        self.g.enviar_a_revision(self.autor)
        self.g.publicar(self.revisor)
        CodigoQR.objects.create(destino_tipo='GUIA', guia=self.g, ubicacion='Torre 3', creado_por=self.sistema)
        self.g.retirar(self.sistema)
        P.entrar_panel(self.client, self.sistema)
        self.client.post(f'/panel/contenidos/guias/{self.g.pk}/eliminar/')
        self.assertTrue(Guia.objects.filter(pk=self.g.pk).exists())

    def test_audit_inmutable(self):
        r = RegistroAuditoria.registrar(self.autor, Accion.CREAR, self.g)
        with self.assertRaises(ValueError):
            r.save()
        with self.assertRaises(ValueError):
            r.delete()


class PanelContenidosTests(TestCase):
    def setUp(self):
        self.sistema, self.autor, self.revisor = P.usuarios()

    def test_crear_enviar_y_publicar_desde_el_panel(self):
        P.entrar_panel(self.client, self.autor)
        r = self.client.post('/panel/contenidos/guias/nuevo/', {
            'titulo': 'Bolsa verde', 'tipo': 'SEPARACION', 'contenedor': 3, 'resumen': 'Orgánicos',
            'cuerpo': '+ Cáscaras', 'fuente_oficial': 'Resolución 2184 de 2019', 'enviar': '1'})
        g = Guia.objects.get(titulo='Bolsa verde')
        self.assertRedirects(r, f'/panel/contenidos/guias/{g.pk}/')
        self.assertEqual(g.estado, E.EN_REVISION)
        self.client.post(f'/panel/contenidos/guias/{g.pk}/publicar/')
        g.refresh_from_db()
        self.assertEqual(g.estado, E.EN_REVISION, 'el autor no puede publicar su propia guía')
        P.entrar_panel(self.client, self.revisor)
        self.client.post(f'/panel/contenidos/guias/{g.pk}/publicar/')
        g.refresh_from_db()
        self.assertEqual((g.estado, g.revisor), (E.PUBLICADO, self.revisor))

    def test_rn05_especial_va_a_posconsumo(self):
        P.entrar_panel(self.client, self.autor)
        r = self.client.post('/panel/contenidos/residuos/nuevo/', {'nombre': 'pilas', 'contenedor': 1, 'es_especial': 'on'})
        self.assertContains(r, 'Punto posconsumo', status_code=200)
        self.client.post('/panel/contenidos/residuos/nuevo/', {'nombre': 'pilas', 'contenedor': 4})
        from .models import Residuo
        self.assertTrue(Residuo.objects.get(nombre='Pilas').es_especial)

    def test_rn09_solo_sistema_elimina(self):
        g = P.guia(self.autor, self.revisor, estado=E.RETIRADO)
        P.entrar_panel(self.client, self.revisor)
        self.client.post(f'/panel/contenidos/guias/{g.pk}/eliminar/')
        self.assertTrue(Guia.objects.filter(pk=g.pk).exists())
        P.entrar_panel(self.client, self.sistema)
        self.client.post(f'/panel/contenidos/guias/{g.pk}/eliminar/')
        self.assertFalse(Guia.objects.filter(pk=g.pk).exists())

    def test_paginas_del_panel(self):
        P.entrar_panel(self.client, self.sistema)
        for url in ['/panel/', '/panel/contenidos/', '/panel/contenidos/?tipo=residuos', '/panel/contenidos/guias/nuevo/',
                    '/panel/revision/', '/panel/puntos/', '/panel/puntos/nuevo/', '/panel/trivia/', '/panel/trivia/nueva/',
                    '/panel/sugerencias/', '/panel/qr/', '/panel/qr/instituciones/', '/panel/estadisticas/',
                    '/panel/estadisticas/?dias=90', '/panel/estadisticas/exportar.csv', '/panel/usuarios/',
                    '/panel/auditoria/', '/cuenta/', '/accounts/2fa/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_rn09_admin_contenido_no_entra_a_secciones_de_sistema(self):
        P.entrar_panel(self.client, self.autor)
        for url in ['/panel/qr/', '/panel/estadisticas/', '/panel/usuarios/', '/panel/auditoria/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
