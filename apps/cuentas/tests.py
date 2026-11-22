"""Pruebas de autenticación y control de acceso (caja blanca y gris).

Cubren: registro con verificación real del correo, ingreso con Google (OIDC con PKCE, simulando solo la
respuesta del servidor de Google), verificación en dos pasos del panel, reautenticación, autorización de
datos (Ley 1581), exportación y supresión de la cuenta, y cifrado del secreto TOTP."""
import re
import time
from unittest import mock
from urllib.parse import parse_qs, urlparse

import jwt
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.socialaccount.models import SocialAccount
from django.core import mail
from django.test import TestCase, override_settings

from apps.auditoria.models import RegistroAuditoria
from apps.core import pruebas as P
from apps.trivia.models import PartidaTrivia

from .models import Consentimiento, Rol, Usuario

GOOGLE = {'google': {'APPS': [{'client_id': 'cliente-prueba.apps.googleusercontent.com', 'secret': 'secreto-prueba', 'key': ''}],
                     'SCOPE': ['openid', 'email', 'profile'], 'AUTH_PARAMS': {'access_type': 'online'},
                     'OAUTH_PKCE_ENABLED': True}}


def id_token(correo, verificado=True, aud='cliente-prueba.apps.googleusercontent.com', sub='1098765432101234567'):
    ahora = int(time.time())
    datos = {'iss': 'https://accounts.google.com', 'aud': aud, 'sub': sub, 'email': correo,
             'email_verified': verificado, 'name': 'Laura Gómez', 'iat': ahora, 'exp': ahora + 600}
    return jwt.encode(datos, 'no-importa', algorithm='HS256')


def codigo_del_correo():
    cuerpo = mail.outbox[-1].body
    return re.search(r'^\s*([A-Z0-9]{4}-?[A-Z0-9]{4}|[A-Z0-9]{6})\s*$', cuerpo, re.M).group(1)


@override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE, VERIFICAR_MX_CORREO=False)
class RegistroConCorreoTests(TestCase):
    datos = {'nombre': 'Laura Gómez', 'email': 'Laura@Ejemplo.co', 'password1': 'Guacamaya-Roja-2026',
             'password2': 'Guacamaya-Roja-2026', 'acepta_datos': 'on', 'mayor_edad': 'on'}

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_registro_visitante_directo_y_nombre_desde_correo(self):
        r = self.client.post('/accounts/signup/', self.datos)
        u = Usuario.objects.get(correo='laura@ejemplo.co')
        self.assertEqual((u.rol, u.nombre), (Rol.VISITANTE, 'Laura Gómez'))
        self.assertTrue(Consentimiento.objects.filter(usuario=u).exists())
        self.assertEqual(self.client.session.get('_auth_user_id'), str(u.pk), 'el visitante entra directo sin trabas')
        self.assertEqual(r.status_code, 302)
        # Si omite el nombre, se toma automáticamente del correo
        self.client.post('/accounts/logout/')
        sin_nombre = {**self.datos, 'nombre': '', 'email': 'carlos.perez@ejemplo.co'}
        self.client.post('/accounts/signup/', sin_nombre)
        u2 = Usuario.objects.get(correo='carlos.perez@ejemplo.co')
        self.assertEqual(u2.nombre, 'Carlos Perez')

    def test_registro_sin_autorizacion_rechazado(self):
        datos = {**self.datos, 'acepta_datos': ''}
        self.client.post('/accounts/signup/', datos)
        self.assertFalse(Usuario.objects.filter(correo='laura@ejemplo.co').exists())

    def test_contrasena_debil_rechazada(self):
        self.client.post('/accounts/signup/', {**self.datos, 'password1': '12345678', 'password2': '12345678'})
        self.assertFalse(Usuario.objects.exists())

    @override_settings(VERIFICAR_MX_CORREO=True)
    def test_dominio_sin_correo_rechazado(self):
        with mock.patch('apps.cuentas.forms.dominio_recibe_correo', return_value=False):
            r = self.client.post('/accounts/signup/', {**self.datos, 'email': 'x@dominio-que-no-existe.co'})
        self.assertContains(r, 'no recibe mensajes')

    def test_bloqueo_por_intentos_fallidos(self):
        u = Usuario.objects.create_user('ana@ejemplo.co', 'Ana', P.CLAVE)
        EmailAddress.objects.create(user=u, email=u.correo, verified=True, primary=True)
        for _ in range(5):
            self.client.post('/accounts/login/', {'login': 'ana@ejemplo.co', 'password': 'mala'})
        r = self.client.post('/accounts/login/', {'login': 'ana@ejemplo.co', 'password': P.CLAVE})
        self.assertNotIn('_auth_user_id', self.client.session, 'tras 5 fallos ni la clave correcta entra')
        self.assertContains(r, 'Demasiados intentos fallidos')

    def test_recuperar_contrasena_con_codigo(self):
        u = Usuario.objects.create_user('ana@ejemplo.co', 'Ana', P.CLAVE)
        EmailAddress.objects.create(user=u, email=u.correo, verified=True, primary=True)
        r = self.client.post('/accounts/password/reset/', {'email': 'ana@ejemplo.co'})
        r = self.client.post(r['Location'], {'code': codigo_del_correo()})
        self.client.post(r['Location'], {'password1': 'Nueva-Clave-Segura-26', 'password2': 'Nueva-Clave-Segura-26'})
        u.refresh_from_db()
        self.assertTrue(u.check_password('Nueva-Clave-Segura-26'))

    def test_correo_inexistente_no_revela_nada(self):
        r = self.client.post('/accounts/password/reset/', {'email': 'nadie@ejemplo.co'})
        self.assertEqual(r.status_code, 302, 'misma respuesta exista o no la cuenta (anti-enumeración)')

    def test_cuenta_inactiva_no_ingresa(self):
        u = Usuario.objects.create_user('ana@ejemplo.co', 'Ana', P.CLAVE)
        EmailAddress.objects.create(user=u, email=u.correo, verified=True, primary=True)
        u.is_active = False
        u.save()
        self.client.post('/accounts/login/', {'login': 'ana@ejemplo.co', 'password': P.CLAVE})
        self.assertNotIn('_auth_user_id', self.client.session)


@override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE)
class GoogleTests(TestCase):
    def _iniciar(self):
        r = self.client.post('/accounts/google/login/')
        url = urlparse(r['Location'])
        self.assertEqual(url.netloc, 'accounts.google.com')
        q = parse_qs(url.query)
        self.assertEqual(q['code_challenge_method'], ['S256'], 'PKCE activo')
        self.assertIn('openid', q['scope'][0])
        return q['state'][0]

    def _volver(self, state, token):
        with mock.patch('allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token',
                        return_value={'access_token': 'ya29.prueba', 'id_token': token, 'expires_in': 3599}) as m:
            r = self.client.get('/accounts/google/login/callback/', {'state': state, 'code': '4/codigo'})
        if m.called:
            self.assertTrue(m.call_args.kwargs.get('pkce_code_verifier'), 'se envía el code_verifier a Google')
        return r

    def test_inicio_por_get_no_permitido(self):
        r = self.client.get('/accounts/google/login/')
        self.assertNotEqual(urlparse(r.get('Location', '')).netloc, 'accounts.google.com',
                            'el flujo solo arranca con POST + CSRF (evita login CSRF)')

    def test_google_crea_visitante_y_pide_autorizacion(self):
        state = self._iniciar()
        r = self._volver(state, id_token('Laura.Gomez@gmail.com'))
        u = Usuario.objects.get(correo='laura.gomez@gmail.com')
        self.assertEqual((u.rol, u.nombre, u.has_usable_password()), (Rol.VISITANTE, 'Laura Gómez', False))
        self.assertTrue(SocialAccount.objects.filter(user=u, provider='google', uid='1098765432101234567').exists())
        self.assertFalse(SocialAccount.objects.get(user=u).socialtoken_set.exists(), 'no se guardan tokens de Google')
        r = self.client.get('/cuenta/')
        self.assertRedirects(r, '/cuenta/autorizacion/?next=/cuenta/')

    def test_correo_no_verificado_rechazado(self):
        state = self._iniciar()
        self._volver(state, id_token('x@gmail.com', verificado=False))
        self.assertFalse(Usuario.objects.filter(correo='x@gmail.com').exists())

    def test_token_de_otra_aplicacion_rechazado(self):
        state = self._iniciar()
        self._volver(state, id_token('x@gmail.com', aud='otra-app.apps.googleusercontent.com'))
        self.assertFalse(Usuario.objects.filter(correo='x@gmail.com').exists())

    def test_state_falso_rechazado(self):
        self._iniciar()
        self._volver('state-inventado', id_token('x@gmail.com'))
        self.assertFalse(Usuario.objects.filter(correo='x@gmail.com').exists())

    def test_admin_autorizado_se_enlaza_y_no_pierde_rol(self):
        admin = Usuario.objects.create_user('darien@gmail.com', 'Darien García', rol=Rol.CONTENIDO)
        state = self._iniciar()
        self._volver(state, id_token('darien@gmail.com', sub='555'))
        admin.refresh_from_db()
        self.assertEqual(admin.rol, Rol.CONTENIDO)
        self.assertEqual(Usuario.objects.filter(correo='darien@gmail.com').count(), 1)
        self.assertTrue(SocialAccount.objects.filter(user=admin, uid='555').exists())

    def test_preregistro_malicioso_pierde_la_contrasena(self):
        """Account pre-hijacking: alguien registró el correo de la víctima sin verificarlo."""
        atacante = Usuario.objects.create_user('victima@gmail.com', 'Atacante', 'Clave-Del-Atacante-1')
        EmailAddress.objects.create(user=atacante, email='victima@gmail.com', verified=False, primary=True)
        state = self._iniciar()
        self._volver(state, id_token('victima@gmail.com', sub='777'))
        atacante.refresh_from_db()
        self.assertFalse(atacante.has_usable_password())


class PanelSeguroTests(TestCase):
    def setUp(self):
        self.sistema, self.autor, self.revisor = P.usuarios()
        for u in (self.sistema, self.autor):
            EmailAddress.objects.create(user=u, email=u.correo, verified=True, primary=True)
        P.consentir(self.sistema, self.autor)

    def test_ingreso_con_contrasena_y_codigo_totp(self):
        secreto = P.activar_totp(self.autor)
        r = self.client.post('/accounts/login/', {'login': 'autor@ecoparce.com.co', 'password': P.CLAVE})
        self.assertRedirects(r, '/accounts/2fa/authenticate/', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session, 'sin el código todavía no hay sesión')
        r = self.client.post('/accounts/2fa/authenticate/', {'code': '000000'})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.client.post('/accounts/2fa/authenticate/', {'code': P.codigo_totp(secreto)})
        self.assertEqual(self.client.session['_auth_user_id'], str(self.autor.pk))
        self.assertEqual(self.client.get('/panel/').status_code, 200)
        self.assertTrue(RegistroAuditoria.objects.filter(accion='INGRESO', usuario=self.autor).exists())

    def test_admin_sin_2fa_debe_activarla(self):
        P.entrar_panel(self.client, self.autor, mfa=False)
        self.assertRedirects(self.client.get('/panel/'), '/accounts/2fa/totp/activate/', fetch_redirect_response=False)

    def test_sesion_sin_paso_mfa_es_expulsada(self):
        P.activar_totp(self.autor)
        P.entrar_panel(self.client, self.autor, mfa=False)
        r = self.client.get('/panel/')
        self.assertIn('/accounts/login/', r['Location'])
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_visitante_no_entra_al_panel(self):
        visitante = Usuario.objects.create_user('v@ejemplo.co', 'Visitante', P.CLAVE)
        P.entrar_panel(self.client, visitante)
        self.assertEqual(self.client.get('/panel/').status_code, 403)
        self.assertEqual(self.client.get('/panel/contenidos/').status_code, 403)

    def test_inactividad_cierra_el_panel(self):
        P.entrar_panel(self.client, self.autor)
        self.client.get('/panel/')
        s = self.client.session
        s['panel_ultima_actividad'] = int(time.time()) - 31 * 60
        s.save()
        self.assertIn('/accounts/login/', self.client.get('/panel/')['Location'])

    def test_secreto_totp_cifrado_en_la_base(self):
        secreto = P.activar_totp(self.autor)
        guardado = Authenticator.objects.get(user=self.autor, type='totp').data['secret']
        self.assertTrue(guardado.startswith('f1:'))
        self.assertNotIn(secreto, guardado)

    def test_admin_no_puede_apagar_su_2fa(self):
        from apps.cuentas.mfa_adapter import MFAAdapter
        P.activar_totp(self.autor)
        self.assertFalse(MFAAdapter().can_delete_authenticator(Authenticator.objects.get(user=self.autor, type='totp')))

    def test_crear_admin_exige_reautenticacion(self):
        P.entrar_panel(self.client, self.sistema)
        s = self.client.session
        for reg in s['account_authentication_methods']:
            reg['at'] = time.time() - 600   # ingresó hace 10 minutos
        s.save()
        r = self.client.get('/panel/usuarios/nuevo/')
        self.assertEqual(r.status_code, 302, 'pide confirmar la identidad con el código')
        P.reautenticar(self.client, self.sistema)
        self.client.post('/panel/usuarios/nuevo/', {'nombre': 'Camilo Ramírez', 'correo': 'Camilo@Gmail.com', 'rol': 'CONTENIDO'})
        u = Usuario.objects.get(correo='camilo@gmail.com')
        self.assertEqual(u.rol, Rol.CONTENIDO)
        self.assertFalse(u.has_usable_password(), 'entra con Google; no se crean contraseñas por él')

    def test_promover_visitante_existente(self):
        v = Usuario.objects.create_user('v@gmail.com', 'Vale')
        P.entrar_panel(self.client, self.sistema)
        P.reautenticar(self.client, self.sistema)
        self.client.post('/panel/usuarios/nuevo/', {'nombre': 'Valentina', 'correo': 'v@gmail.com', 'rol': 'CONTENIDO'})
        v.refresh_from_db()
        self.assertEqual(v.rol, Rol.CONTENIDO)

    def test_desactivar_cierra_sus_sesiones(self):
        otro = self.client_class()
        P.entrar_panel(otro, self.autor)
        self.assertEqual(otro.get('/panel/').status_code, 200)
        P.entrar_panel(self.client, self.sistema)
        P.reautenticar(self.client, self.sistema)
        self.client.post(f'/panel/usuarios/{self.autor.pk}/', {'nombre': self.autor.nombre, 'rol': 'CONTENIDO'})
        self.autor.refresh_from_db()
        self.assertFalse(self.autor.is_active)
        self.assertNotEqual(otro.get('/panel/').status_code, 200)

    def test_no_se_desactiva_a_si_mismo(self):
        P.entrar_panel(self.client, self.sistema)
        P.reautenticar(self.client, self.sistema)
        self.client.post(f'/panel/usuarios/{self.sistema.pk}/', {'nombre': self.sistema.nombre, 'rol': 'SISTEMA'})
        self.sistema.refresh_from_db()
        self.assertTrue(self.sistema.is_active)

    def test_restablecer_2fa_de_otro(self):
        P.activar_totp(self.autor)
        P.entrar_panel(self.client, self.sistema)
        P.reautenticar(self.client, self.sistema)
        self.client.post(f'/panel/usuarios/{self.autor.pk}/', {'restablecer_mfa': '1'})
        self.assertFalse(Authenticator.objects.filter(user=self.autor).exists())

    def test_roles(self):
        self.assertTrue(self.sistema.es_admin_sistema())
        self.assertFalse(self.autor.es_admin_sistema())
        self.assertTrue(self.autor.es_personal)
        self.assertFalse(Usuario.objects.create_user('z@e.co', 'Z').es_personal)
        self.assertEqual(Usuario.objects.create_superuser('s@e.co', 'S', P.CLAVE).rol, Rol.SISTEMA)

    def test_solicitud_y_aprobacion_de_administrador(self):
        from .models import EstadoSolicitudAdmin, SolicitudAdmin
        visitante = Usuario.objects.create_user('nuevo_admin@ejemplo.co', 'Sofía Torres', P.CLAVE)
        P.consentir(visitante)
        self.client.force_login(visitante)
        # Inicio personalizado para usuario registrado
        r_home = self.client.get('/')
        self.assertContains(r_home, '¡Hola,')
        self.assertContains(r_home, 'Medallas 3D')
        # Enviar solicitud para ser administrador
        r_sol = self.client.post('/cuenta/solicitar-admin/', {'motivo': 'Quiero apoyar revisando guías de reciclaje.'})
        self.assertRedirects(r_sol, '/cuenta/')
        sol = SolicitudAdmin.objects.get(usuario=visitante)
        self.assertEqual(sol.estado, EstadoSolicitudAdmin.PENDIENTE)
        # El administrador del sistema la aprueba desde /panel/usuarios/
        otro = self.client_class()
        P.entrar_panel(otro, self.sistema)
        r_ap = otro.post(f'/panel/usuarios/solicitud/{sol.pk}/', {'accion': 'aprobar_contenido'})
        self.assertRedirects(r_ap, '/panel/usuarios/')
        visitante.refresh_from_db()
        sol.refresh_from_db()
        self.assertEqual(visitante.rol, Rol.CONTENIDO)
        self.assertEqual(sol.estado, EstadoSolicitudAdmin.APROBADA)
        self.assertTrue(RegistroAuditoria.objects.filter(usuario=self.sistema, detalle__icontains='Aprobó solicitud').exists())

    def test_flujo_e2e_login_navegacion_logout_y_proteccion_rutas(self):
        v = Usuario.objects.create_user('e2e@ejemplo.co', 'Camila E2E', P.CLAVE)
        EmailAddress.objects.create(user=v, email=v.correo, verified=True, primary=True)
        P.consentir(v)
        # 1. Inicio de sesión real
        r_login = self.client.post('/accounts/login/', {'login': v.correo, 'password': P.CLAVE})
        self.assertEqual(r_login.status_code, 302)
        self.assertEqual(self.client.session.get('_auth_user_id'), str(v.pk))
        # 2. Navegación interna y visibilidad del botón de cerrar sesión
        for ruta in ['/', '/cuenta/', '/guias/', '/escanear/', '/trivia/', '/sugerencias/']:
            r = self.client.get(ruta)
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, 'data-cerrar-sesion')
        # 3. Cierre de sesión destruye sesión y redirige a /accounts/login/
        r_out = self.client.post('/accounts/logout/')
        self.assertRedirects(r_out, '/accounts/login/')
        self.assertNotIn('_auth_user_id', self.client.session)
        # 4. No puede volver a rutas privadas sin autenticarse nuevamente
        r_priv = self.client.get('/cuenta/')
        self.assertEqual(r_priv.status_code, 302)
        self.assertIn('/accounts/login/', r_priv['Location'])
        self.assertEqual(r_priv['Cache-Control'], 'no-store')


class DatosPersonalesTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.v = Usuario.objects.create_user('v@gmail.com', 'Vale Ruiz')

    def _entrar(self, consentir=True):
        if consentir:
            P.consentir(self.v)
        P.entrar_panel(self.client, self.v, mfa=False, metodo='socialaccount')
        if not consentir:
            Consentimiento.objects.filter(usuario=self.v).delete()

    def test_sin_autorizacion_no_usa_la_cuenta(self):
        self.client.force_login(self.v)
        self.assertRedirects(self.client.get('/cuenta/'), '/cuenta/autorizacion/?next=/cuenta/')
        self.client.post('/cuenta/autorizacion/', {'acepto': 'on', 'next': '/cuenta/'})
        self.assertEqual(self.client.get('/cuenta/').status_code, 200)

    def test_rechazar_autorizacion_borra_la_cuenta(self):
        self.client.force_login(self.v)
        self.client.post('/cuenta/autorizacion/', {'decision': 'rechazo'})
        self.assertFalse(Usuario.objects.filter(pk=self.v.pk).exists())

    def test_redireccion_abierta_bloqueada(self):
        self.client.force_login(self.v)
        r = self.client.post('/cuenta/autorizacion/', {'acepto': 'on', 'next': 'https://sitio-malicioso.com/'})
        self.assertEqual(r['Location'], '/cuenta/')

    def test_exportar_mis_datos(self):
        self._entrar()
        r = self.client.get('/cuenta/mis-datos.json')
        datos = r.json()
        self.assertEqual(datos['cuenta']['correo'], 'v@gmail.com')
        self.assertIn('attachment', r['Content-Disposition'])
        self.assertIn('insignias_trivia', datos)
        self.assertIn('acepta_marketing', datos['autorizaciones'][0])

    def test_comunicaciones_baja_en_un_clic(self):
        self._entrar()
        c = Consentimiento.objects.get(usuario=self.v)
        self.assertFalse(c.acepta_marketing)
        self.client.post('/cuenta/comunicaciones/', {'accion': 'alta'})
        c.refresh_from_db()
        self.assertTrue(c.acepta_marketing)
        self.client.post('/cuenta/comunicaciones/', {'accion': 'baja'})
        c.refresh_from_db()
        self.assertFalse(c.acepta_marketing)

    def test_eliminar_cuenta_anonimiza(self):
        self._entrar()
        PartidaTrivia.objects.create(usuario=self.v, puntaje=3, total_preguntas=5)
        r = self.client.post('/cuenta/eliminar/', {'confirmacion': 'eliminar'})
        self.assertRedirects(r, '/')
        self.assertFalse(Usuario.objects.filter(pk=self.v.pk).exists())
        self.assertIsNone(PartidaTrivia.objects.get().usuario)

    def test_eliminar_exige_ingreso_reciente(self):
        self._entrar()
        s = self.client.session
        for reg in s['account_authentication_methods']:
            reg['at'] = time.time() - 3600
        s.save()
        self.client.post('/cuenta/eliminar/', {'confirmacion': 'ELIMINAR'})
        self.assertTrue(Usuario.objects.filter(pk=self.v.pk).exists())

    def test_partida_de_visitante_queda_en_su_cuenta(self):
        from apps.trivia.tests import pregunta
        autor = Usuario.objects.create_user('a@e.co', 'A', rol=Rol.CONTENIDO)
        for n in range(5):
            pregunta(autor, n)
        self._entrar()
        self.client.post('/trivia/nueva/')
        self.assertEqual(PartidaTrivia.objects.get().usuario, self.v)


class EncabezadosTests(TestCase):
    def test_csp_permite_solo_google_como_destino_de_formularios(self):
        r = self.client.get('/accounts/login/')
        self.assertIn("form-action 'self' https://accounts.google.com", r['Content-Security-Policy'])
        self.assertEqual(r['Cache-Control'], 'no-store')

    def test_security_txt(self):
        r = self.client.get('/.well-known/security.txt')
        self.assertContains(r, 'Contact: mailto:')
        self.assertContains(r, 'Expires:')

    def test_flujos_desactivados(self):
        self.assertEqual(self.client.get('/accounts/email/').status_code, 404)

    def test_contrasena_segura_medidor_y_argon2id(self):
        from django.core.exceptions import ValidationError
        from apps.cuentas.validadores import ClaveSeguraValidator

        # 1. La página de registro incluye el medidor en vivo sin jerga técnica visible
        r = self.client.get('/accounts/signup/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'clave-medidor')
        self.assertNotContains(r, 'Argon2id')

        # 2. Validador rechaza contraseñas sin mayúscula, número, especial, cortas o con correo/nombre
        val = ClaveSeguraValidator()
        dummy = Usuario(correo='andres.lopez@gmail.com', nombre='Andrés López')
        for mala in [
            'Ab1!cort',               # 8 caracteres (no mayor a 8)
            'sinmayuscula1!',         # falta mayúscula
            'SINMINUSCULA1!',         # falta minúscula
            'SinNumeroEspecial!',     # falta número
            'SinEspecial1234',        # falta carácter especial
            'Andres#2026Segura',      # contiene su nombre
            'andres.lopez#2026A',     # contiene su correo
        ]:
            with self.assertRaises(ValidationError, msg=f'Debió rechazar: {mala}'):
                val.validate(mala, user=dummy)

        # 3. Contraseña segura pasa y se almacena encriptada con Argon2id (nunca texto plano)
        fuerte = 'EcoParce#2026!'
        val.validate(fuerte, user=dummy)
        u = Usuario.objects.create_user('seguro@gmail.com', 'Andrés López', fuerte)
        self.assertTrue(u.password.startswith('argon2$'))
        self.assertNotIn(fuerte, u.password)
        self.assertTrue(u.check_password(fuerte))

    def test_version_json_control_versiones_y_marca(self):
        from apps.core.context_processors import app_version
        ver = app_version()

        # 1. Endpoint /version.json sin caché devuelve la versión activa
        r_ver = self.client.get('/version.json')
        self.assertEqual(r_ver.status_code, 200)
        self.assertEqual(r_ver.json()['version'], ver)
        self.assertIn('no-store', r_ver['Cache-Control'])

        # 2. Pie de página incluye la marca, el banner de actualización, EcoBot y Cache-Control sin caché vieja
        r_home = self.client.get('/')
        self.assertContains(r_home, 'Francisco Navarro, Danixa Herrera y Darien García')
        self.assertContains(r_home, 'banner-actualizacion')
        self.assertContains(r_home, 'ecobot-fab')
        self.assertNotContains(r_home, 'Ilustración IA')
        self.assertIn('no-cache', r_home['Cache-Control'])
        self.assertIn('microphone=(self)', r_home['Permissions-Policy'])

        # 3. /panel/versiones/ exige administrador y muestra el historial de versiones
        self.assertEqual(self.client.get('/panel/versiones/').status_code, 302)
        _, autor, _ = P.usuarios()
        P.entrar_panel(self.client, autor)
        r_panel = self.client.get('/panel/versiones/')
        self.assertEqual(r_panel.status_code, 200)
        self.assertContains(r_panel, f'v{ver}')
        self.assertContains(r_panel, 'Control de versiones')
        self.assertContains(r_panel, 'Francisco Navarro, Danixa Herrera y Darien García')

    def test_healthcheck_y_api_asistente_ecobot(self):
        from apps.core.context_processors import app_version

        # 1. Healthcheck de producción verifica BD y responde sin caché
        r_hp = self.client.get('/health/')
        self.assertEqual(r_hp.status_code, 200)
        self.assertEqual(r_hp.json()['status'], 'ok')
        self.assertEqual(r_hp.json()['version'], app_version())
        self.assertIn('no-store', r_hp['Cache-Control'])

        # 2. API EcoBot consulta residuos reales publicados y normas Res. 2184
        _, autor, revisor = P.usuarios()
        P.residuo('Botella PET transparente', autor, revisor, codigo='BLANCA')
        r_bot = self.client.get('/asistente/consultar/', {'q': 'botella'})
        self.assertEqual(r_bot.status_code, 200)
        datos = r_bot.json()
        self.assertTrue(datos['encontrado'])
        self.assertEqual(datos['codigo'], 'BLANCA')
        self.assertIn('no-store', r_bot['Cache-Control'])

        r_norm = self.client.get('/asistente/consultar/', {'q': 'resolucion 2184'})
        self.assertEqual(r_norm.status_code, 200)
        self.assertTrue(r_norm.json()['encontrado'])

        # 3. Término inexistente devuelve sugerencia segura sin romper
        r_no = self.client.get('/asistente/consultar/', {'q': '<script>alert(1)</script>'})
        self.assertEqual(r_no.status_code, 200)
        self.assertFalse(r_no.json()['encontrado'])
