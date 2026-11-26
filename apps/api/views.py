"""Endpoints REST (GET y POST) de EcoParce protegidos por el API Gateway."""
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import connection
from django.http import JsonResponse

from apps.buscador.escaner import CODIGO_VALIDO, analizar, buscar_producto
from apps.buscador.models import Busqueda, Sugerencia
from apps.contenidos.models import EstadoContenido, Guia, PuntoEntrega, Residuo
from apps.core.cifrado_e2e import cifrar_sobre_e2e
from apps.core.context_processors import app_version, google_configurado
from apps.core.rls import filtrar_por_rls, obtener_contexto_rls
from apps.core.seguridad import evento, limitar
from apps.core.texto import normalizar
from apps.trivia.models import PartidaTrivia

from .gateway import endpoint_gateway, extraer_api_key
from .models import ApiKey, RegistroGateway
from .oauth2 import (
    OAUTH_ISSUER,
    emitir_par_tokens_oauth2,
    introspeccionar_token_oauth2,
    revocar_token_oauth2,
    rotar_refresh_token,
)


def _ok(request, datos, status=200):
    """Construye una respuesta JSON estándar exitosa con request_id del API Gateway."""
    return JsonResponse(
        {
            'ok': True,
            'data': datos,
            'request_id': str(getattr(request, 'gateway_request_id', '')),
        },
        status=status,
    )


def _error(request, codigo, mensaje, status=400):
    """Construye una respuesta JSON estándar de error sin filtrar trazas internas."""
    return JsonResponse(
        {
            'ok': False,
            'error': {'codigo': codigo, 'mensaje': mensaje},
            'request_id': str(getattr(request, 'gateway_request_id', '')),
        },
        status=status,
    )


@endpoint_gateway(metodos=('GET',))
def estado_api(request):
    """GET /api/v1/estado/ — Estado del servicio, seguridad, cifrado y RLS."""
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
        db_ok = True
    except Exception:
        db_ok = False
    return _ok(
        request,
        {
            'servicio': 'EcoParce API Gateway',
            'version': app_version(),
            'base_datos': {'conectada': db_ok, 'motor': connection.vendor},
            'seguridad': {
                'cifrado_cuentas': 'MultiFernet (AES-128-CBC + HMAC-SHA256)',
                'cifrado_e2e': 'AES-256-GCM (HKDF-SHA256) + TLS',
                'hash_contrasenas': 'Argon2id',
                'oauth2': 'RFC 6749/7519/7009/7662/8414/9700 + Google OIDC PKCE',
                'rls_capa_aplicacion': True,
                'rls_nativo_postgresql': connection.vendor == 'postgresql',
                'google_oauth_configurado': google_configurado(),
                'smtp_configurado': bool(getattr(settings, 'EMAIL_HOST', '')),
                'verificacion_correo_codigo': bool(getattr(settings, 'ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED', False)),
                'contexto_rls': obtener_contexto_rls()['role'],
            },
        },
        status=200 if db_ok else 503,
    )


@endpoint_gateway(metodos=('GET',))
def listar_guias(request):
    """GET /api/v1/guias/ — Guías educativas publicadas (RN-01)."""
    guias = Guia.publicadas.select_related('contenedor').order_by('tipo', 'titulo')
    datos = [
        {
            'id': g.pk,
            'slug': g.slug,
            'titulo': g.titulo,
            'tipo': g.tipo,
            'contenedor': g.contenedor.codigo if g.contenedor else None,
            'resumen': g.resumen,
            'fuente_oficial': g.fuente_oficial,
            'url': g.get_absolute_url(),
        }
        for g in guias
    ]
    return _ok(request, {'total': len(datos), 'guias': datos})


@endpoint_gateway(metodos=('GET',))
def buscar_residuos(request):
    """GET /api/v1/buscar/?q=<termino> — Buscador público de residuos (RN-01, RN-08)."""
    termino = (request.GET.get('q') or '').strip()[:80]
    if not termino:
        return _error(request, 'MISSING_QUERY', 'Envía el parámetro q con el residuo a consultar.', status=400)

    objetivo = normalizar(termino)
    encontrados = []
    for r in Residuo.objects.filter(estado=EstadoContenido.PUBLICADO).select_related('contenedor'):
        claves = [normalizar(r.nombre)] + [normalizar(s) for s in (r.sinonimos or '').split(',') if s.strip()]
        if any(objetivo in c or c in objetivo for c in claves if c):
            encontrados.append({
                'id': r.pk,
                'nombre': r.nombre,
                'contenedor': r.contenedor.codigo,
                'contenedor_nombre': r.contenedor.nombre,
                'es_especial': r.es_especial,
                'preparacion': r.preparacion,
            })

    Busqueda.objects.create(termino=termino, encontrado=bool(encontrados))
    return _ok(request, {'termino': termino, 'total': len(encontrados), 'resultados': encontrados})


@endpoint_gateway(metodos=('GET',))
def listar_puntos(request):
    """GET /api/v1/puntos/?localidad=...&limite=50 — Puntos posconsumo activos."""
    localidad = (request.GET.get('localidad') or '').strip()[:80]
    try:
        limite = min(max(int(request.GET.get('limite', '50')), 1), 100)
    except ValueError:
        limite = 50
    qs = PuntoEntrega.objects.filter(activo=True).order_by('localidad', 'nombre')
    if localidad:
        qs = qs.filter(localidad__icontains=localidad)
    total = qs.count()
    puntos = [
        {
            'id': p.pk,
            'nombre': p.nombre,
            'direccion': p.direccion,
            'localidad': p.localidad,
            'horario': p.horario,
            'recibe': p.recibe,
            'latitud': p.latitud,
            'longitud': p.longitud,
            'fuente': p.fuente,
        }
        for p in qs[:limite]
    ]
    return _ok(request, {'total': total, 'mostrados': len(puntos), 'puntos': puntos})


@endpoint_gateway(metodos=('GET', 'POST'))
def escanear_codigo(request, codigo=None):
    """GET /api/v1/escanear/<codigo>/ o POST /api/v1/escanear/ {"codigo": "..."} — Consulta remota Open Food Facts."""
    if request.method == 'POST':
        datos = request.gateway_json or {}
        codigo = str(datos.get('codigo', '')).strip()
    else:
        codigo = str(codigo or '').strip()

    if not CODIGO_VALIDO.match(codigo):
        return _error(request, 'INVALID_BARCODE', 'El código de barras debe tener entre 8 y 14 dígitos.', status=400)

    fuente, producto = buscar_producto(codigo)
    if not producto:
        return _ok(request, {'codigo': codigo, 'encontrado': False, 'partes': []})

    partes = analizar(producto)
    nombre = producto.get('product_name_es') or producto.get('product_name') or 'Producto'
    return _ok(
        request,
        {
            'codigo': codigo,
            'encontrado': True,
            'fuente': fuente,
            'producto': nombre,
            'marca': producto.get('brands') or '',
            'partes': partes,
        },
    )


@endpoint_gateway(metodos=('POST',), requiere_auth=True, requiere_escritura=True)
def crear_sugerencia(request):
    """POST /api/v1/sugerencias/ — Registra una sugerencia de residuo (requiere X-API-Key escritura o sesión)."""
    datos = request.gateway_json or {}
    termino = str(datos.get('termino', '')).strip()
    comentario = str(datos.get('comentario', '')).strip()
    if len(termino) < 2 or len(termino) > 80:
        return _error(request, 'INVALID_TERM', 'El campo termino debe tener entre 2 y 80 caracteres.', status=400)
    if len(comentario) > 300:
        return _error(request, 'INVALID_COMMENT', 'El campo comentario no puede superar 300 caracteres.', status=400)

    sug = Sugerencia.objects.create(
        termino=termino,
        comentario=comentario,
        usuario=request.api_actor,
    )
    return _ok(
        request,
        {
            'id': sug.pk,
            'termino': sug.termino,
            'estado': sug.estado,
            'fecha_hora': sug.fecha_hora.isoformat(),
        },
        status=201,
    )


@endpoint_gateway(metodos=('GET',), requiere_auth=True)
def resumen_cuenta(request):
    """GET /api/v1/cuenta/resumen/ — Resumen aislado por RLS (soporta sobre E2E AES-256-GCM con ?e2e=1)."""
    usuario = request.api_actor
    partidas = filtrar_por_rls(PartidaTrivia.objects.filter(finalizada_en__isnull=False), usuario)
    sugerencias = filtrar_por_rls(Sugerencia.objects.all(), usuario)
    carga = {
        'usuario': {
            'id': usuario.pk,
            'correo': usuario.correo,
            'nombre': usuario.nombre,
            'rol': usuario.rol,
            'mfa_activo': usuario.tiene_mfa(),
        },
        'partidas_finalizadas': partidas.count(),
        'sugerencias_enviadas': sugerencias.count(),
    }
    if request.GET.get('e2e') == '1' or request.META.get('HTTP_X_E2E_ENCRYPT') == '1':
        return _ok(request, {'e2e': cifrar_sobre_e2e(carga, aad=f'user:{usuario.pk}')})
    return _ok(request, carga)


@endpoint_gateway(metodos=('GET',), solo_sistema=True)
def logs_gateway(request):
    """GET /api/v1/gateway/logs/ — Bitácora inmutable del API Gateway (solo rol SISTEMA)."""
    try:
        limite = min(max(int(request.GET.get('limite', '30')), 1), 100)
    except ValueError:
        limite = 30
    registros = RegistroGateway.objects.all()[:limite]
    return _ok(
        request,
        {
            'total': len(registros),
            'registros': [
                {
                    'request_id': str(r.request_id),
                    'metodo': r.metodo,
                    'ruta': r.ruta,
                    'codigo_estado': r.codigo_estado,
                    'duracion_ms': r.duracion_ms,
                    'bloqueado': r.bloqueado,
                    'motivo_bloqueo': r.motivo_bloqueo,
                    'fecha_hora': r.fecha_hora.isoformat(),
                }
                for r in registros
            ],
        },
    )


@endpoint_gateway(metodos=('POST',))
def oauth_token(request):
    """POST /api/v1/oauth/token/ — Servidor OAuth 2.0 (RFC 6749/9700): emite Bearer JWT + Refresh Token rotativo."""
    if not limitar(request, 'oauth2_token', maximo=10, segundos=60):
        return _error(request, 'RATE_LIMIT', 'Demasiados intentos de autenticación OAuth 2.0.', status=429)

    datos = request.gateway_json or {}
    grant = str(datos.get('grant_type', '')).strip().lower()

    if grant == 'client_credentials':
        secreto = str(datos.get('client_secret') or '').strip() or extraer_api_key(request)
        llave = ApiKey.validar(secreto)
        if llave is None:
            evento('oauth2_token_rechazado', request, grant=grant)
            return _error(request, 'INVALID_CLIENT', 'Credenciales de cliente inválidas.', status=401)
        scope = 'read write' if llave.permite_escritura() else 'read'
        token_resp = emitir_par_tokens_oauth2(llave.propietario, scope=scope)
        evento('oauth2_token_emitido', request, usuario=llave.propietario, grant=grant)
        return _ok(request, token_resp, status=200)

    if grant == 'password':
        correo = str(datos.get('email') or datos.get('username') or '').strip().lower()
        clave = str(datos.get('password') or '')
        usuario = authenticate(request, username=correo, password=clave)
        if usuario is None or not usuario.is_active:
            evento('oauth2_token_rechazado', request, grant=grant)
            return _error(request, 'INVALID_GRANT', 'Credenciales incorrectas o cuenta inactiva.', status=401)
        token_resp = emitir_par_tokens_oauth2(usuario, scope='read write')
        evento('oauth2_token_emitido', request, usuario=usuario, grant=grant)
        return _ok(request, token_resp, status=200)

    if grant == 'refresh_token':
        rt = str(datos.get('refresh_token') or '').strip()
        nuevo_par, err = rotar_refresh_token(rt)
        if err or nuevo_par is None:
            evento('oauth2_refresh_rechazado', request, motivo=err or 'INVALID_REFRESH')
            return _error(request, err or 'INVALID_GRANT', 'Refresh token inválido, expirado o reutilizado.', status=401)
        evento('oauth2_token_rotado', request)
        return _ok(request, nuevo_par, status=200)

    return _error(
        request,
        'UNSUPPORTED_GRANT_TYPE',
        'grant_type soportados: client_credentials, password, refresh_token.',
        status=400,
    )


@endpoint_gateway(metodos=('POST',), requiere_auth=True)
def oauth_introspect(request):
    """POST /api/v1/oauth/introspect/ — Introspección estándar OAuth 2.0 (RFC 7662)."""
    datos = request.gateway_json or {}
    token = str(datos.get('token') or '').strip() or extraer_api_key(request)
    return _ok(request, introspeccionar_token_oauth2(token))


def oauth_metadata(request):
    """GET /.well-known/oauth-authorization-server — Metadatos OAuth 2.0 (RFC 8414)."""
    base = settings.SITE_URL.rstrip('/')
    resp = JsonResponse({
        'issuer': OAUTH_ISSUER,
        'authorization_endpoint': f'{base}/accounts/google/login/',
        'token_endpoint': f'{base}/api/v1/oauth/token/',
        'revocation_endpoint': f'{base}/api/v1/oauth/revoke/',
        'introspection_endpoint': f'{base}/api/v1/oauth/introspect/',
        'userinfo_endpoint': f'{base}/api/v1/oauth/userinfo/',
        'grant_types_supported': ['authorization_code', 'client_credentials', 'password', 'refresh_token'],
        'code_challenge_methods_supported': ['S256'],
        'token_endpoint_auth_methods_supported': ['client_secret_post', 'bearer'],
        'scopes_supported': ['openid', 'email', 'profile', 'read', 'write'],
        'response_types_supported': ['code'],
    })
    resp['Cache-Control'] = 'public, max-age=3600'
    return resp


@endpoint_gateway(metodos=('POST',), requiere_auth=True)
def oauth_revoke(request):
    """POST /api/v1/oauth/revoke/ — Revocación de token OAuth 2.0 (RFC 7009)."""
    datos = request.gateway_json or {}
    token = str(datos.get('token') or '').strip() or extraer_api_key(request)
    revocado = revocar_token_oauth2(token)
    evento('oauth2_token_revocado', request, usuario=request.api_actor, ok=revocado)
    return _ok(request, {'revoked': revocado})


@endpoint_gateway(metodos=('GET',), requiere_auth=True)
def oauth_userinfo(request):
    """GET /api/v1/oauth/userinfo/ — Endpoint OIDC/OAuth 2.0 UserInfo protegido."""
    u = request.api_actor
    return _ok(
        request,
        {
            'sub': str(u.pk),
            'email': u.correo,
            'name': u.nombre,
            'role': u.rol,
            'mfa_enabled': u.tiene_mfa(),
            'oauth2_scope': getattr(request, 'oauth_claims', {}).get('scope', 'api_key'),
        },
    )


@endpoint_gateway(metodos=('GET',))
def openapi_spec(request):
    """GET /api/v1/openapi.json — Especificación OpenAPI 3.0.3 del API Gateway de EcoParce."""
    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': 'EcoParce API Gateway',
            'version': app_version(),
            'description': (
                'API REST segura de EcoParce con filtros WAF (SQLi, XSS, Path Traversal), '
                'autenticación por API Key (SHA-256), rate limiting, Row-Level Security (RLS) '
                'y bitácora inmutable de auditoría.'
            ),
        },
        'servers': [{'url': f"{settings.SITE_URL.rstrip('/')}/api/v1"}],
        'components': {
            'securitySchemes': {
                'ApiKeyAuth': {'type': 'apiKey', 'in': 'header', 'name': 'X-API-Key'},
                'BearerAuth': {'type': 'http', 'scheme': 'bearer'},
            },
        },
        'paths': {
            '/estado/': {
                'get': {'summary': 'Estado del sistema, cifrado y RLS', 'responses': {'200': {'description': 'Servicio operativo'}}},
            },
            '/guias/': {
                'get': {'summary': 'Listar guías educativas publicadas (RN-01)', 'responses': {'200': {'description': 'Lista de guías'}}},
            },
            '/buscar/': {
                'get': {
                    'summary': 'Buscar residuo por nombre o sinónimo',
                    'parameters': [{'name': 'q', 'in': 'query', 'required': True, 'schema': {'type': 'string'}}],
                    'responses': {'200': {'description': 'Resultados de búsqueda'}, '400': {'description': 'Parámetro faltante o bloqueado por WAF'}},
                },
            },
            '/puntos/': {
                'get': {
                    'summary': 'Consultar puntos posconsumo activos',
                    'parameters': [
                        {'name': 'localidad', 'in': 'query', 'required': False, 'schema': {'type': 'string'}},
                        {'name': 'limite', 'in': 'query', 'required': False, 'schema': {'type': 'integer', 'default': 50}},
                    ],
                    'responses': {'200': {'description': 'Lista de puntos'}},
                },
            },
            '/escanear/': {
                'post': {
                    'summary': 'Clasificar empaque por código de barras (Open Food Facts)',
                    'requestBody': {
                        'required': True,
                        'content': {'application/json': {'schema': {'type': 'object', 'properties': {'codigo': {'type': 'string'}}, 'required': ['codigo']}}},
                    },
                    'responses': {'200': {'description': 'Análisis de empaque y bolsa'}},
                },
            },
            '/escanear/{codigo}/': {
                'get': {
                    'summary': 'Consultar código de barras vía GET',
                    'parameters': [{'name': 'codigo', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                    'responses': {'200': {'description': 'Análisis de empaque y bolsa'}},
                },
            },
            '/sugerencias/': {
                'post': {
                    'summary': 'Crear sugerencia de residuo (requiere API Key de escritura)',
                    'security': [{'ApiKeyAuth': []}, {'BearerAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'termino': {'type': 'string', 'minLength': 2, 'maxLength': 80},
                                        'comentario': {'type': 'string', 'maxLength': 300},
                                    },
                                    'required': ['termino'],
                                },
                            },
                        },
                    },
                    'responses': {'201': {'description': 'Sugerencia creada'}, '401': {'description': 'No autenticado'}, '403': {'description': 'Permiso insuficiente'}},
                },
            },
            '/cuenta/resumen/': {
                'get': {
                    'summary': 'Resumen de la cuenta autenticada (aislado por RLS)',
                    'security': [{'ApiKeyAuth': []}, {'BearerAuth': []}],
                    'responses': {'200': {'description': 'Resumen de cuenta'}, '401': {'description': 'No autenticado'}},
                },
            },
            '/gateway/logs/': {
                'get': {
                    'summary': 'Bitácora inmutable del API Gateway (solo rol SISTEMA)',
                    'security': [{'ApiKeyAuth': []}, {'BearerAuth': []}],
                    'responses': {'200': {'description': 'Registros recientes'}, '403': {'description': 'Solo administrador del sistema'}},
                },
            },
        },
    }
    return JsonResponse(spec)
