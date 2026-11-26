"""Pruebas integrales de cifrado de cuentas, RLS, API Gateway (GET/POST), filtros WAF y código de correo."""
import json
import re
from unittest import mock

from cryptography.fernet import Fernet
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings

from apps.api.models import ApiKey, PermisoApi, RegistroGateway
from apps.buscador.models import Sugerencia
from apps.contenidos.models import Contenedor, EstadoContenido, Guia, PuntoEntrega, Residuo, TipoGuia
from apps.core import pruebas as P
from apps.core.cifrado import PREFIJO_CIFRADO, esta_cifrado
from apps.core.rls import filtrar_por_rls, generar_sql_rls, obtener_contexto_rls
from apps.cuentas.models import Consentimiento, Rol, SolicitudAdmin, Usuario


class CifradoYRlsTests(TestCase):
    def test_cuentas_se_cifran_en_base_de_datos(self):
        u = Usuario.objects.create_user('secreto@ejemplo.co', 'María Fernanda López', P.CLAVE)
        sol = SolicitudAdmin.objects.create(usuario=u, motivo='Soy coordinadora ambiental del colegio')

        with connection.cursor() as cur:
            cur.execute('SELECT nombre, correo_hash FROM usuario WHERE id = %s', [u.pk])
            nombre_raw, correo_hash = cur.fetchone()
            cur.execute('SELECT motivo FROM solicitud_admin WHERE id = %s', [sol.pk])
            motivo_raw = cur.fetchone()[0]

        self.assertTrue(esta_cifrado(nombre_raw), 'nombre debe guardarse cifrado en BD')
        self.assertNotIn('María', nombre_raw)
        self.assertEqual(len(correo_hash), 64)
        self.assertTrue(esta_cifrado(motivo_raw), 'motivo debe guardarse cifrado en BD')
        self.assertNotIn('coordinadora', motivo_raw)

        # Al leer desde el ORM se descifra transparentemente
        u_bd = Usuario.objects.get(pk=u.pk)
        sol_bd = SolicitudAdmin.objects.get(pk=sol.pk)
        self.assertEqual(u_bd.nombre, 'María Fernanda López')
        self.assertEqual(sol_bd.motivo, 'Soy coordinadora ambiental del colegio')

    def test_rotacion_de_claves_multifernet(self):
        clave_vieja = Fernet.generate_key().decode('ascii')
        clave_nueva = Fernet.generate_key().decode('ascii')

        with override_settings(DB_CLAVES_CIFRADO=[clave_vieja], MFA_CLAVES_CIFRADO=[]):
            u = Usuario.objects.create_user('rotacion@ejemplo.co', 'Carlos Rotación', P.CLAVE)

        with override_settings(DB_CLAVES_CIFRADO=[clave_nueva, clave_vieja], MFA_CLAVES_CIFRADO=[]):
            u_leido = Usuario.objects.get(pk=u.pk)
            self.assertEqual(u_leido.nombre, 'Carlos Rotación')
            self.assertTrue(PREFIJO_CIFRADO.startswith('enc:'))

    def test_rls_aisla_filas_por_usuario_y_genera_sql_postgresql(self):
        u1 = Usuario.objects.create_user('u1@ejemplo.co', 'Usuario Uno', P.CLAVE, rol=Rol.VISITANTE)
        u2 = Usuario.objects.create_user('u2@ejemplo.co', 'Usuario Dos', P.CLAVE, rol=Rol.VISITANTE)
        admin = Usuario.objects.create_user('admin@ejemplo.co', 'Admin Sistema', P.CLAVE, rol=Rol.SISTEMA)

        Consentimiento.objects.create(usuario=u1, version='2026-11')
        Consentimiento.objects.create(usuario=u2, version='2026-11')
        SolicitudAdmin.objects.create(usuario=u1, motivo='Motivo 1')
        SolicitudAdmin.objects.create(usuario=u2, motivo='Motivo 2')

        self.assertEqual(Consentimiento.para_usuario_rls(u1).count(), 1)
        self.assertEqual(Consentimiento.para_usuario_rls(u1).first().usuario_id, u1.pk)
        self.assertEqual(SolicitudAdmin.para_usuario_rls(u2).count(), 1)
        self.assertEqual(SolicitudAdmin.para_usuario_rls(admin).count(), 2)
        self.assertEqual(filtrar_por_rls(Consentimiento.objects.all(), None).count(), 0)

        sql = generar_sql_rls()
        self.assertNotIn('USING (true)', sql, 'no debe haber reglas RLS abiertas USING (true)')
        self.assertNotIn('WITH CHECK (true)', sql, 'no debe haber reglas RLS abiertas WITH CHECK (true)')
        self.assertIn('FOR UPDATE\n    USING (false)', sql, 'auditoría debe bloquear UPDATE en BD')
        self.assertIn('FOR DELETE\n    USING (false)', sql, 'auditoría debe bloquear DELETE en BD')
        for tabla in ('usuario', 'consentimiento', 'solicitud_admin', 'registro_auditoria', 'api_clave', 'api_gateway_log'):
            self.assertIn(f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY;', sql)
            self.assertIn(f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY;', sql)
        self.assertEqual(obtener_contexto_rls()['role'], 'ANON')


class ApiGatewayTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_user('sys@ecoparce.co', 'Admin Sys', P.CLAVE, rol=Rol.SISTEMA)
        self.editor = Usuario.objects.create_user('ed@ecoparce.co', 'Editor', P.CLAVE, rol=Rol.CONTENIDO)
        self.visitante = Usuario.objects.create_user('vis@ejemplo.co', 'Visitante Uno', P.CLAVE, rol=Rol.VISITANTE)
        self.otro = Usuario.objects.create_user('otro@ejemplo.co', 'Visitante Dos', P.CLAVE, rol=Rol.VISITANTE)

        self.key_admin, self.raw_admin = ApiKey.generar('Admin Key', self.admin, PermisoApi.LECTURA_ESCRITURA)
        self.key_vis, self.raw_vis = ApiKey.generar('Visitante RW', self.visitante, PermisoApi.LECTURA_ESCRITURA)
        self.key_ro, self.raw_ro = ApiKey.generar('Visitante RO', self.visitante, PermisoApi.LECTURA)

        blanca = Contenedor.objects.get(codigo=Contenedor.BLANCA)
        self.guia = Guia.objects.create(
            titulo='Bolsa blanca', slug='bolsa-blanca-api', tipo=TipoGuia.SEPARACION, contenedor=blanca,
            resumen='Aprovechables', cuerpo='Limpios y secos', fuente_oficial='Res. 2184 de 2019',
            estado=EstadoContenido.PUBLICADO, autor=self.editor, revisor=self.admin,
        )
        self.residuo = Residuo.objects.create(
            nombre='Botella PET', sinonimos='plastico, gaseosa', contenedor=blanca,
            preparacion='Enjuagar; aplastar',
            estado=EstadoContenido.PUBLICADO, autor=self.editor, revisor=self.admin,
        )
        PuntoEntrega.objects.create(
            nombre='Punto Centro', direccion='Cra 7 # 10-20', localidad='Santa Fe',
            horario='L-V 8-17', recibe='Pilas', activo=True,
        )

    def test_get_endpoints_publicos_y_cabeceras_gateway(self):
        r_estado = self.client.get('/api/v1/estado/')
        self.assertEqual(r_estado.status_code, 200)
        self.assertEqual(r_estado['X-Gateway'], 'EcoParce-API-Gateway/1.0')
        self.assertIn('X-Request-ID', r_estado)
        self.assertEqual(r_estado['Cache-Control'], 'no-store')
        data = r_estado.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['data']['base_datos']['conectada'])

        r_guias = self.client.get('/api/v1/guias/')
        self.assertEqual(r_guias.status_code, 200)
        self.assertGreaterEqual(r_guias.json()['data']['total'], 1)

        r_buscar = self.client.get('/api/v1/buscar/?q=botella')
        self.assertEqual(r_buscar.status_code, 200)
        self.assertEqual(r_buscar.json()['data']['total'], 1)

        r_puntos = self.client.get('/api/v1/puntos/?localidad=Santa')
        self.assertEqual(r_puntos.status_code, 200)
        self.assertEqual(r_puntos.json()['data']['total'], 1)

    def test_post_sugerencia_con_api_key_permisos_y_rls(self):
        payload = json.dumps({'termino': 'Cápsula de café', 'comentario': 'Aluminio con café'})

        # Sin API Key -> 401
        r_sin = self.client.post('/api/v1/sugerencias/', data=payload, content_type='application/json')
        self.assertEqual(r_sin.status_code, 401)

        # Con API Key de solo lectura -> 403
        r_ro = self.client.post(
            '/api/v1/sugerencias/', data=payload, content_type='application/json',
            HTTP_X_API_KEY=self.raw_ro,
        )
        self.assertEqual(r_ro.status_code, 403)

        # Con API Key de lectura y escritura -> 201 Created
        r_ok = self.client.post(
            '/api/v1/sugerencias/', data=payload, content_type='application/json',
            HTTP_X_API_KEY=self.raw_vis,
        )
        self.assertEqual(r_ok.status_code, 201)
        self.assertTrue(Sugerencia.objects.filter(termino='Cápsula de café', usuario=self.visitante).exists())

        # Resumen cuenta aislado por RLS
        r_resumen = self.client.get('/api/v1/cuenta/resumen/', HTTP_X_API_KEY=self.raw_vis)
        self.assertEqual(r_resumen.status_code, 200)
        self.assertEqual(r_resumen.json()['data']['sugerencias_enviadas'], 1)
        self.assertEqual(r_resumen.json()['data']['usuario']['nombre'], 'Visitante Uno')

        _, raw_otro = ApiKey.generar('Otro Key', self.otro, PermisoApi.LECTURA)
        r_otro = self.client.get('/api/v1/cuenta/resumen/', HTTP_X_API_KEY=raw_otro)
        self.assertEqual(r_otro.status_code, 200)
        self.assertEqual(r_otro.json()['data']['sugerencias_enviadas'], 0)

    def test_post_escanear_producto_remoto_simulado(self):
        fake_prod = {
            'product_name_es': 'Agua Brisa',
            'brands': 'Brisa',
            'packagings': [{'material': 'en:pet', 'shape': 'en:bottle'}],
        }
        with mock.patch('apps.api.views.buscar_producto', return_value=('Open Food Facts', fake_prod)):
            r = self.client.post(
                '/api/v1/escanear/',
                data=json.dumps({'codigo': '7702004003508'}),
                content_type='application/json',
                HTTP_X_API_KEY=self.raw_vis,
            )
        self.assertEqual(r.status_code, 200)
        body = r.json()['data']
        self.assertTrue(body['encontrado'])
        self.assertEqual(body['producto'], 'Agua Brisa')
        self.assertEqual(body['partes'][0]['codigo'], Contenedor.BLANCA)

    def test_filtros_seguridad_waf_rate_limit_y_bitacora_inmutable(self):
        # SQL Injection bloqueado
        r_sqli = self.client.get("/api/v1/buscar/?q=botella' UNION SELECT * FROM usuario--")
        self.assertEqual(r_sqli.status_code, 400)
        self.assertEqual(r_sqli.json()['error']['codigo'], 'SQLI_DETECTED')

        # XSS en POST bloqueado
        r_xss = self.client.post(
            '/api/v1/sugerencias/',
            data=json.dumps({'termino': '<script>alert(1)</script>'}),
            content_type='application/json',
            HTTP_X_API_KEY=self.raw_vis,
        )
        self.assertEqual(r_xss.status_code, 400)
        self.assertEqual(r_xss.json()['error']['codigo'], 'XSS_DETECTED')

        # Path Traversal bloqueado
        r_trav = self.client.get('/api/v1/buscar/?q=../../etc/passwd')
        self.assertEqual(r_trav.status_code, 400)
        self.assertEqual(r_trav.json()['error']['codigo'], 'PATH_TRAVERSAL')

        # API Key inválida bloqueada
        r_bad_key = self.client.get('/api/v1/cuenta/resumen/', HTTP_X_API_KEY='ecp_invalida_1234567890123456')
        self.assertEqual(r_bad_key.status_code, 401)
        self.assertEqual(r_bad_key.json()['error']['codigo'], 'INVALID_API_KEY')

        # Rate limit por API Key
        key_mini, raw_mini = ApiKey.generar('Mini', self.visitante, PermisoApi.LECTURA, limite_por_minuto=2)
        self.assertEqual(self.client.get('/api/v1/estado/', HTTP_X_API_KEY=raw_mini).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/estado/', HTTP_X_API_KEY=raw_mini).status_code, 200)
        r_rl = self.client.get('/api/v1/estado/', HTTP_X_API_KEY=raw_mini)
        self.assertEqual(r_rl.status_code, 429)
        self.assertEqual(r_rl.json()['error']['codigo'], 'RATE_LIMIT')

        # Logs del Gateway: solo SISTEMA puede leerlos
        self.assertEqual(self.client.get('/api/v1/gateway/logs/', HTTP_X_API_KEY=self.raw_vis).status_code, 403)
        r_logs = self.client.get('/api/v1/gateway/logs/', HTTP_X_API_KEY=self.raw_admin)
        self.assertEqual(r_logs.status_code, 200)
        self.assertGreaterEqual(r_logs.json()['data']['total'], 5)

        # Inmutabilidad de RegistroGateway
        log_row = RegistroGateway.objects.first()
        with self.assertRaises(ValueError):
            log_row.save()
        with self.assertRaises(ValueError):
            log_row.delete()


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION='mandatory',
    ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED=True,
    VERIFICAR_MX_CORREO=False,
)
class CodigoCorreoVerificacionTests(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()

    def test_registro_envia_codigo_y_verifica_correo(self):
        datos = {
            'nombre': 'Andrea Código',
            'email': 'andrea.codigo@ejemplo.co',
            'password1': 'Guacamaya-Roja-2026',
            'password2': 'Guacamaya-Roja-2026',
            'acepta_datos': 'on',
            'mayor_edad': 'on',
        }
        r = self.client.post('/accounts/signup/', datos)
        self.assertEqual(r.status_code, 302)
        self.assertGreaterEqual(len(mail.outbox), 1, 'debe enviarse correo con código de verificación')
        cuerpo = mail.outbox[-1].body
        match = re.search(r'^\s*([A-Z0-9]{4}-?[A-Z0-9]{4}|[A-Z0-9]{6})\s*$', cuerpo, re.M)
        self.assertIsNotNone(match, f'no se encontró código en el correo: {cuerpo}')
        codigo = match.group(1)

        # Enviar el código recibido en el correo confirma la cuenta e inicia sesión
        r2 = self.client.post(r['Location'], {'code': codigo})
        self.assertEqual(r2.status_code, 302)
        u = Usuario.objects.get(correo='andrea.codigo@ejemplo.co')
        self.assertEqual(self.client.session.get('_auth_user_id'), str(u.pk))


class PanelCalidadOpenApiPwaTests(TestCase):
    def test_openapi_spec_valida(self):
        r = self.client.get('/api/v1/openapi.json')
        self.assertEqual(r.status_code, 200)
        spec = r.json()
        self.assertEqual(spec['openapi'], '3.0.3')
        self.assertIn('/estado/', spec['paths'])
        self.assertIn('/sugerencias/', spec['paths'])
        self.assertIn('ApiKeyAuth', spec['components']['securitySchemes'])

    def test_pwa_service_worker_y_pagina_offline(self):
        r_sw = self.client.get('/sw.js')
        self.assertEqual(r_sw.status_code, 200)
        self.assertIn('javascript', r_sw['Content-Type'])
        self.assertEqual(r_sw['Service-Worker-Allowed'], '/')
        cuerpo = r_sw.content.decode('utf-8')
        self.assertIn('/offline/', cuerpo)
        self.assertIn("'/panel/'", cuerpo)

        r_off = self.client.get('/offline/')
        self.assertEqual(r_off.status_code, 200)
        self.assertContains(r_off, 'Bolsa Blanca')
        self.assertContains(r_off, 'Resolución 2184')

    def test_panel_calidad_solo_sistema_y_gestion_api_keys(self):
        admin, editor, _ = P.usuarios()

        # Editor de contenido no puede entrar a /panel/calidad/
        P.entrar_panel(self.client, editor)
        self.assertEqual(self.client.get('/panel/calidad/').status_code, 403)

        # Admin del sistema entra, ve métricas, crea y revoca una API Key
        P.entrar_panel(self.client, admin)
        r = self.client.get('/panel/calidad/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Row-Level Security (RLS)')
        self.assertContains(r, 'OpenAPI')

        r_crear = self.client.post('/panel/calidad/llaves/crear/', {
            'nombre': 'Postman Calidad',
            'permisos': PermisoApi.LECTURA_ESCRITURA,
            'limite': '90',
        })
        self.assertEqual(r_crear.status_code, 302)
        llave = ApiKey.objects.get(nombre='Postman Calidad')
        self.assertTrue(llave.activa)

        # La clave plana aparece una vez al recargar el tablero
        r_post = self.client.get('/panel/calidad/')
        self.assertContains(r_post, 'ecp_')

        # Revocar desde el panel
        r_rev = self.client.post(f'/panel/calidad/llaves/{llave.pk}/alternar/')
        self.assertEqual(r_rev.status_code, 302)
        llave.refresh_from_db()
        self.assertFalse(llave.activa)

    def test_oauth2_jwt_completo_y_revocacion(self):
        cache.clear()
        u = Usuario.objects.create_user('oauth2@ejemplo.co', 'Camila OAuth', P.CLAVE, rol=Rol.VISITANTE)
        _, raw_key = ApiKey.generar('Cliente OAuth2', u, PermisoApi.LECTURA_ESCRITURA)

        # 1. Grant client_credentials -> emite JWT Bearer
        r_tok = self.client.post(
            '/api/v1/oauth/token/',
            data=json.dumps({'grant_type': 'client_credentials', 'client_secret': raw_key}),
            content_type='application/json',
        )
        self.assertEqual(r_tok.status_code, 200)
        token_data = r_tok.json()['data']
        self.assertEqual(token_data['token_type'], 'Bearer')
        jwt_token = token_data['access_token']

        # 2. Consumir /api/v1/oauth/userinfo/ con Bearer JWT
        r_info = self.client.get('/api/v1/oauth/userinfo/', HTTP_AUTHORIZATION=f'Bearer {jwt_token}')
        self.assertEqual(r_info.status_code, 200)
        self.assertEqual(r_info.json()['data']['email'], 'oauth2@ejemplo.co')
        self.assertEqual(r_info.json()['data']['name'], 'Camila OAuth')

        # 3. Grant password -> emite JWT Bearer
        r_pwd = self.client.post(
            '/api/v1/oauth/token/',
            data=json.dumps({'grant_type': 'password', 'email': 'oauth2@ejemplo.co', 'password': P.CLAVE}),
            content_type='application/json',
        )
        self.assertEqual(r_pwd.status_code, 200)
        self.assertIn('access_token', r_pwd.json()['data'])

        # 4. Revocar JWT (RFC 7009) y comprobar que ya no entra
        r_rev = self.client.post(
            '/api/v1/oauth/revoke/',
            data=json.dumps({'token': jwt_token}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        self.assertEqual(r_rev.status_code, 200)
        self.assertTrue(r_rev.json()['data']['revoked'])

        r_after = self.client.get('/api/v1/oauth/userinfo/', HTTP_AUTHORIZATION=f'Bearer {jwt_token}')
        self.assertEqual(r_after.status_code, 401)

    def test_auditoria_oauth2_rfc9700_scopes_rotacion_introspect_y_e2e_aes256gcm(self):
        from apps.core.cifrado_e2e import descifrar_sobre_e2e

        cache.clear()
        u = Usuario.objects.create_user('audit.oauth@ejemplo.co', 'Sofía Auditoría', P.CLAVE, rol=Rol.VISITANTE)
        _, raw_ro = ApiKey.generar('Solo Lectura OAuth', u, PermisoApi.LECTURA)

        # 1. RFC 8414: Discovery metadata
        r_meta = self.client.get('/.well-known/oauth-authorization-server')
        self.assertEqual(r_meta.status_code, 200)
        meta = r_meta.json()
        self.assertIn('S256', meta['code_challenge_methods_supported'])
        self.assertIn('refresh_token', meta['grant_types_supported'])

        # 2. Scope enforcement: llave solo lectura -> JWT scope='read' -> POST bloqueado con 403 INSUFFICIENT_SCOPE
        r_tok = self.client.post(
            '/api/v1/oauth/token/',
            data=json.dumps({'grant_type': 'client_credentials', 'client_secret': raw_ro}),
            content_type='application/json',
        )
        self.assertEqual(r_tok.status_code, 200)
        self.assertEqual(r_tok['Cache-Control'], 'no-store')
        self.assertEqual(r_tok['Pragma'], 'no-cache')
        par1 = r_tok.json()['data']
        self.assertEqual(par1['scope'], 'read')

        r_post_ro = self.client.post(
            '/api/v1/sugerencias/',
            data=json.dumps({'termino': 'Intento sin scope write'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {par1['access_token']}",
        )
        self.assertEqual(r_post_ro.status_code, 403)
        self.assertEqual(r_post_ro.json()['error']['codigo'], 'INSUFFICIENT_SCOPE')

        # 3. Confusión de token impedida: un refresh_token NO sirve como Bearer access_token
        r_conf = self.client.get('/api/v1/oauth/userinfo/', HTTP_AUTHORIZATION=f"Bearer {par1['refresh_token']}")
        self.assertEqual(r_conf.status_code, 401)

        # 4. RFC 7662: Introspección activa
        r_int = self.client.post(
            '/api/v1/oauth/introspect/',
            data=json.dumps({'token': par1['access_token']}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {par1['access_token']}",
        )
        self.assertEqual(r_int.status_code, 200)
        self.assertTrue(r_int.json()['data']['active'])

        # 5. Rotación de refresh token + detección de reutilización (RFC 9700)
        r_rot = self.client.post(
            '/api/v1/oauth/token/',
            data=json.dumps({'grant_type': 'refresh_token', 'refresh_token': par1['refresh_token']}),
            content_type='application/json',
        )
        self.assertEqual(r_rot.status_code, 200)
        par2 = r_rot.json()['data']
        self.assertNotEqual(par2['refresh_token'], par1['refresh_token'])

        # Reutilizar rt1 dispara REFRESH_TOKEN_REUSE y revoca TODA la familia (incluido access2)
        r_replay = self.client.post(
            '/api/v1/oauth/token/',
            data=json.dumps({'grant_type': 'refresh_token', 'refresh_token': par1['refresh_token']}),
            content_type='application/json',
        )
        self.assertEqual(r_replay.status_code, 401)
        self.assertEqual(r_replay.json()['error']['codigo'], 'REFRESH_TOKEN_REUSE')
        self.assertEqual(
            self.client.get('/api/v1/oauth/userinfo/', HTTP_AUTHORIZATION=f"Bearer {par2['access_token']}").status_code,
            401,
        )

        # 6. Cifrado autenticado E2E AES-256-GCM en /api/v1/cuenta/resumen/?e2e=1
        r_e2e = self.client.get('/api/v1/cuenta/resumen/?e2e=1', HTTP_X_API_KEY=raw_ro)
        self.assertEqual(r_e2e.status_code, 200)
        sobre = r_e2e.json()['data']['e2e']
        self.assertEqual(sobre['alg'], 'AES-256-GCM')
        descifrado = descifrar_sobre_e2e(sobre, aad=f'user:{u.pk}')
        self.assertEqual(descifrado['usuario']['nombre'], 'Sofía Auditoría')
        with self.assertRaises(ValueError):
            descifrar_sobre_e2e(sobre, aad='user:99999')

    def test_pwa_extremo_a_extremo_y_cabeceras_endurecidas(self):
        from pathlib import Path
        from PIL import Image
        from django.conf import settings

        # Verificar manifest.webmanifest e iconos 192x192 y 512x512 reales
        manifest_path = Path(settings.BASE_DIR) / 'static' / 'manifest.webmanifest'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        self.assertEqual(manifest['display'], 'standalone')
        sizes = {ic['sizes'] for ic in manifest['icons']}
        self.assertIn('192x192', sizes)
        self.assertIn('512x512', sizes)
        for ic in manifest['icons']:
            rel = ic['src'].lstrip('/')
            p = Path(settings.BASE_DIR) / rel
            self.assertTrue(p.exists(), f'falta icono PWA {rel}')
            w, h = Image.open(p).size
            self.assertEqual(f'{w}x{h}', ic['sizes'])

        # Verificar cabeceras endurecidas y enlaces PWA en la portada
        r_home = self.client.get('/')
        self.assertEqual(r_home.status_code, 200)
        self.assertContains(r_home, 'manifest.webmanifest')
        self.assertIn("object-src 'none'", r_home['Content-Security-Policy'])
        self.assertIn("worker-src 'self'", r_home['Content-Security-Policy'])
        self.assertIn('payment=()', r_home['Permissions-Policy'])
        self.assertIn('usb=()', r_home['Permissions-Policy'])
        self.assertEqual(r_home['X-Permitted-Cross-Domain-Policies'], 'none')
        self.assertEqual(r_home['X-DNS-Prefetch-Control'], 'off')


