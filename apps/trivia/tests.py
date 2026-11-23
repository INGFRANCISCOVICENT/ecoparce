from django.test import TestCase

from apps.core import pruebas as P

from .models import OpcionTrivia, PartidaTrivia, PreguntaTrivia


def pregunta(autor, n, correctas=(True, False, False)):
    p = PreguntaTrivia.objects.create(enunciado=f'Pregunta {n}', explicacion=f'Explicación {n}', autor=autor)
    for i, c in enumerate(correctas, 1):
        OpcionTrivia.objects.create(pregunta=p, texto=f'Opción {i}', es_correcta=c, orden=i)
    p.activa = p.validar()
    p.save()
    return p


class TriviaTests(TestCase):
    def setUp(self):
        _, self.autor, _ = P.usuarios()
        self.preguntas = [pregunta(self.autor, n) for n in range(7)]

    def test_rn07_validacion(self):
        mala = pregunta(self.autor, 'x', correctas=(True, True))
        self.assertFalse(mala.validar())
        sola = pregunta(self.autor, 'y', correctas=(True,))
        self.assertIn('Debe tener entre 2 y 4 opciones.', sola.errores())

    def test_rf08_partida_de_cinco(self):
        partida = PartidaTrivia.nueva()
        self.assertEqual(partida.total_preguntas, 5)
        for i in range(5):
            p = partida.siguiente_pregunta()
            partida.responder(p, p.opciones.get(orden=1 if i < 3 else 2))
        self.assertIsNone(partida.siguiente_pregunta())
        self.assertEqual(partida.finalizar(), 3)

    def test_no_se_responde_dos_veces(self):
        partida = PartidaTrivia.nueva()
        p = partida.siguiente_pregunta()
        partida.responder(p, p.opcion_correcta())
        partida.responder(p, p.opcion_correcta())
        self.assertEqual(partida.puntaje, 1)

    def test_flujo_web(self):
        self.client.post('/trivia/nueva/')
        for _ in range(5):
            r = self.client.get('/trivia/jugar/')
            p = r.context['pregunta']
            r = self.client.post('/trivia/jugar/', {'pregunta': p.pk, 'opcion': p.opcion_correcta().pk})
            self.assertContains(self.client.get(r['Location']), '¡Así es!')
        r = self.client.get('/trivia/resultado/')
        self.assertContains(r, '5 / 5')
        self.assertIsNotNone(PartidaTrivia.objects.get().finalizada_en)

    def test_panel_crear_pregunta_rn07(self):
        P.entrar_panel(self.client, self.autor)
        datos = {'enunciado': '¿Dónde va el vidrio?', 'dificultad': 1, 'explicacion': 'En la blanca.',
                 'opcion_1': 'Blanca', 'opcion_2': '', 'opcion_3': '', 'opcion_4': '', 'correcta': '1'}
        r = self.client.post('/panel/trivia/nueva/', datos)
        self.assertContains(r, 'al menos dos opciones')
        datos['opcion_2'] = 'Negra'
        self.client.post('/panel/trivia/nueva/', {**datos, 'activar': '1'})
        p = PreguntaTrivia.objects.get(enunciado='¿Dónde va el vidrio?')
        self.assertTrue(p.activa)
        self.assertEqual(p.opcion_correcta().texto, 'Blanca')

    def test_niveles_e_insignias_guardadas_en_bd(self):
        from apps.cuentas.models import Usuario
        from .models import InsigniaUsuario, progreso_niveles

        visitante = Usuario.objects.create_user('jugadora@ejemplo.co', 'Camila', P.CLAVE)
        P.consentir(visitante)
        self.client.force_login(visitante)

        # Inicialmente solo Nivel 1 está desbloqueado
        prog = progreso_niveles(usuario=visitante)
        self.assertTrue(prog['desbloqueados'][1])
        self.assertFalse(prog['desbloqueados'][2])

        # Completar Nivel 1 con 5/5 desbloquea Nivel 2 e insignias en BD
        self.client.post('/trivia/nueva/', {'nivel': '1'})
        for _ in range(5):
            r = self.client.get('/trivia/jugar/')
            p = r.context['pregunta']
            self.client.post('/trivia/jugar/', {'pregunta': p.pk, 'opcion': p.opcion_correcta().pk})
        r = self.client.get('/trivia/resultado/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Semilla Verde')

        codigos = set(InsigniaUsuario.objects.filter(usuario=visitante).values_list('codigo', flat=True))
        self.assertIn('primera_semilla', codigos)
        self.assertIn('explorador_bolsas', codigos)
        self.assertIn('vuelo_perfecto', codigos)
        self.assertTrue(progreso_niveles(usuario=visitante)['desbloqueados'][2])

        # Ahora puede jugar Nivel 2 y desbloquear Guardián del Reciclaje + Nivel 3
        self.client.post('/trivia/nueva/', {'nivel': '2'})
        partida2 = PartidaTrivia.objects.filter(usuario=visitante).order_by('-pk').first()
        self.assertEqual(partida2.nivel, 2)
        for _ in range(5):
            r = self.client.get('/trivia/jugar/')
            p = r.context['pregunta']
            self.client.post('/trivia/jugar/', {'pregunta': p.pk, 'opcion': p.opcion_correcta().pk})
        self.client.get('/trivia/resultado/')
        codigos = set(InsigniaUsuario.objects.filter(usuario=visitante).values_list('codigo', flat=True))
        self.assertIn('guardian_reciclaje', codigos)
        self.assertTrue(progreso_niveles(usuario=visitante)['desbloqueados'][3])

    def test_insignias_solo_por_puntos_y_dificultad_progresiva(self):
        from apps.cuentas.models import Usuario
        from .models import InsigniaUsuario, progreso_niveles

        visitante = Usuario.objects.create_user('cero@ejemplo.co', 'Mateo', P.CLAVE)
        P.consentir(visitante)
        self.client.force_login(visitante)

        # Con 0 puntos NO se otorga ninguna insignia ni se desbloquea Nivel 2
        self.client.post('/trivia/nueva/', {'nivel': '1'})
        for _ in range(5):
            r = self.client.get('/trivia/jugar/')
            p = r.context['pregunta']
            incorrecta = p.opciones.filter(es_correcta=False).first()
            self.client.post('/trivia/jugar/', {'pregunta': p.pk, 'opcion': incorrecta.pk})
        self.client.get('/trivia/resultado/')
        self.assertEqual(InsigniaUsuario.objects.filter(usuario=visitante).count(), 0)
        self.assertFalse(progreso_niveles(usuario=visitante)['desbloqueados'][2])

        # Nivel 2 exige 4/5 puntos (con 3/5 no desbloquea Nivel 3 ni insignia)
        PartidaTrivia.objects.create(usuario=visitante, nivel=1, puntaje=3, total_preguntas=5,
                                     finalizada_en=PartidaTrivia.objects.first().finalizada_en)
        self.assertTrue(progreso_niveles(usuario=visitante)['desbloqueados'][2])
        PartidaTrivia.objects.create(usuario=visitante, nivel=2, puntaje=3, total_preguntas=5,
                                     finalizada_en=PartidaTrivia.objects.first().finalizada_en)
        self.assertFalse(progreso_niveles(usuario=visitante)['desbloqueados'][3])

    def test_modos_de_trivia_y_celebracion_3d(self):
        # Modo BOLSAS y Modo MITOS inician correctamente
        r_bolsas = self.client.post('/trivia/nueva/', {'modo': 'BOLSAS'})
        self.assertRedirects(r_bolsas, '/trivia/jugar/')
        self.assertEqual(PartidaTrivia.objects.order_by('-pk').first().modo, 'BOLSAS')

        r_mitos = self.client.post('/trivia/nueva/', {'modo': 'MITOS'})
        self.assertRedirects(r_mitos, '/trivia/jugar/')
        self.assertEqual(PartidaTrivia.objects.order_by('-pk').first().modo, 'MITOS')

        # Al pasar Nivel 1 (5/5) se muestra la celebración 3D "¡FELICIDADES, PASASTE DE NIVEL!"
        self.client.post('/trivia/nueva/', {'modo': 'NIVELES', 'nivel': '1'})
        for _ in range(5):
            r = self.client.get('/trivia/jugar/')
            p = r.context['pregunta']
            self.client.post('/trivia/jugar/', {'pregunta': p.pk, 'opcion': p.opcion_correcta().pk})
        r_res = self.client.get('/trivia/resultado/')
        self.assertContains(r_res, '¡FELICIDADES, PASASTE DE NIVEL!')
        self.assertContains(r_res, 'medalla-3d')

    def test_video_interactivo_arcade_reto_y_certificado(self):
        from apps.cuentas.models import Usuario

        # Visitante anónimo ve el video interactivo, el simulador arcade y el reto diario,
        # pero el certificado personalizado le invita a registrarse.
        r_anon = self.client.get('/trivia/')
        self.assertEqual(r_anon.status_code, 200)
        self.assertContains(r_anon, 'eco-video-player')
        self.assertContains(r_anon, 'eco-video-canvas')
        self.assertContains(r_anon, 'eco-arcade')
        self.assertContains(r_anon, 'reto-diario-btn')
        self.assertContains(r_anon, 'trivia_video.js')
        self.assertNotContains(r_anon, 'data-generar-certificado')
        self.assertIn("script-src 'self'", r_anon['Content-Security-Policy'])

        # Usuario autenticado desbloquea el botón de Certificado Digital PNG
        visitante = Usuario.objects.create_user('cert@ejemplo.co', 'Sofía', P.CLAVE)
        P.consentir(visitante)
        self.client.force_login(visitante)
        r_auth = self.client.get('/trivia/')
        self.assertContains(r_auth, 'data-generar-certificado')
        self.assertContains(r_auth, 'Sofía')

        # Búsqueda por voz progresiva disponible en /buscar/
        r_busc = self.client.get('/buscar/')
        self.assertEqual(r_busc.status_code, 200)
        self.assertContains(r_busc, 'btn-voz-buscar')

        # Contenido visual enriquecido en inicio (/) y guías (/guias/)
        r_home = self.client.get('/')
        self.assertEqual(r_home.status_code, 200)
        self.assertContains(r_home, 'eco-viaje')
        self.assertContains(r_home, 'data-flip-card')
        self.assertNotContains(r_home, 'eco-showcase')

        r_guias = self.client.get('/guias/')
        self.assertEqual(r_guias.status_code, 200)
        self.assertContains(r_guias, 'data-eco-check')
        self.assertContains(r_guias, 'eco-cartel-gen')
        self.assertContains(r_guias, 'cartel.js')
