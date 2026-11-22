from django.test import TestCase

from apps.contenidos.models import EstadoContenido as E
from apps.core import pruebas as P

from .models import Busqueda, Sugerencia
from .views import buscar_residuos


class BuscadorTests(TestCase):
    def setUp(self):
        _, self.autor, self.revisor = P.usuarios()
        P.residuo('Botella plástica', self.autor, self.revisor, sinonimos='botella PET, envase plástico')
        P.residuo('Caja de leche', self.autor, self.revisor, sinonimos='tetrapak, multicapa')
        P.residuo('Cáscaras de fruta', self.autor, self.revisor, codigo='VERDE', sinonimos='cáscara de banano')
        P.residuo('Borrador oculto', self.autor, estado=E.BORRADOR)

    def test_rf03_sin_tildes_ni_mayusculas_y_por_sinonimo(self):
        self.assertEqual(buscar_residuos('BOTELLA PLASTICA')[0].nombre, 'Botella plástica')
        self.assertEqual(buscar_residuos('Tetrapak')[0].nombre, 'Caja de leche')
        self.assertEqual(buscar_residuos('cascara de banano')[0].nombre, 'Cáscaras de fruta')

    def test_rn01_no_encuentra_borradores(self):
        self.assertEqual(buscar_residuos('borrador oculto'), [])

    def test_rf10_registro_anonimo(self):
        self.client.get('/buscar/?q=Tetrapák')
        self.client.get('/buscar/?q=esponja de brillo')
        b = list(Busqueda.objects.order_by('fecha_hora').values_list('termino', 'encontrado'))
        self.assertEqual(b, [('tetrapak', True), ('esponja de brillo', False)])
        campos = {f.name for f in Busqueda._meta.get_fields()}
        self.assertFalse(campos & {'ip', 'ip_address', 'usuario', 'user_agent'}, 'RN-08: sin datos personales')

    def test_resultado_y_no_encontrado(self):
        self.assertContains(self.client.get('/buscar/?q=botella'), 'Bolsa blanca')
        self.assertContains(self.client.get('/buscar/?q=esponja'), 'Aún no tengo ese residuo')

    def test_rf13_sugerencia_con_limite_y_trampa(self):
        r = self.client.post('/sugerencias/', {'termino': 'esponja de brillo', 'comentario': '¿dónde va?'})
        self.assertRedirects(r, '/buscar/')
        self.client.post('/sugerencias/', {'termino': 'robot', 'sitio_web': 'http://spam'})
        self.assertEqual(list(Sugerencia.objects.values_list('termino', flat=True)), ['esponja de brillo'])
        for _ in range(5):
            self.client.post('/sugerencias/', {'termino': 'otra cosa'})
        self.assertLessEqual(Sugerencia.objects.count(), 5)

    def test_panel_atender_sugerencia(self):
        s = Sugerencia.objects.create(termino='esponja')
        sistema = P.Usuario.objects.get(correo='sistema@ecoparce.com.co')
        P.entrar_panel(self.client, sistema)
        r = self.client.post(f'/panel/sugerencias/{s.pk}/atender/', {'accion': 'crear'})
        self.assertRedirects(r, '/panel/contenidos/residuos/nuevo/?nombre=esponja')
        s.refresh_from_db()
        self.assertEqual((s.estado, s.atendida_por), ('ATENDIDA', sistema))
