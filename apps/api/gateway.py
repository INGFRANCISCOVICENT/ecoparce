"""API Gateway de EcoParce: filtros WAF defensivos, autenticación por API Key, rate limit y bitácora."""
import json
import re
import time
import uuid
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

from apps.core.rls import aplicar_contexto_db
from apps.core.seguridad import evento, huella, limitar

from .models import ApiKey, RegistroGateway
from .oauth2 import validar_token_oauth2

MAX_PAYLOAD_BYTES = 64 * 1024  # 64 KB máximo en peticiones JSON de API

PATRONES_SEGURIDAD = [
    ('SQLI_DETECTED', re.compile(
        r"(?i)(\bunion\b\s+\bselect\b|\bor\b\s+1\s*=\s*1\b|;\s*(drop|delete|alter|truncate)\b|--\s|/\*.*\*/)"
    )),
    ('XSS_DETECTED', re.compile(
        r'(?i)(<\s*script\b|javascript\s*:|on(error|load|click|mouseover)\s*=|<\s*iframe\b)'
    )),
    ('PATH_TRAVERSAL', re.compile(r'(\.\./|\.\.\\|%2e%2e)', re.IGNORECASE)),
    ('NULL_BYTE', re.compile(r'(\x00|%00)', re.IGNORECASE)),
]


def extraer_api_key(request):
    """Lee la llave desde X-API-Key o Authorization: Bearer <clave>."""
    clave = (request.META.get('HTTP_X_API_KEY') or '').strip()
    if clave:
        return clave
    auth = (request.META.get('HTTP_AUTHORIZATION') or '').strip()
    if auth.lower().startswith('bearer '):
        return auth[7:].strip()
    return ''


def inspeccionar_texto(texto):
    """Devuelve el código de amenaza si el texto dispara algún filtro de seguridad, o None."""
    if not texto:
        return None
    muestra = str(texto)
    for codigo, patron in PATRONES_SEGURIDAD:
        if patron.search(muestra):
            return codigo
    return None


def _inspeccionar_estructura(dato):
    """Recorre recursivamente diccionarios y listas JSON buscando patrones maliciosos (SQLi/XSS/Traversal)."""
    if isinstance(dato, str):
        return inspeccionar_texto(dato)
    if isinstance(dato, dict):
        for k, v in dato.items():
            hallazgo = inspeccionar_texto(k) or _inspeccionar_estructura(v)
            if hallazgo:
                return hallazgo
    elif isinstance(dato, list):
        for item in dato:
            hallazgo = _inspeccionar_estructura(item)
            if hallazgo:
                return hallazgo
    return None


def _registrar_gateway(request, status, inicio, bloqueado=False, motivo=''):
    """Persiste un evento inmutable en RegistroGateway y emite log estructurado si fue bloqueado."""
    duracion = int((time.monotonic() - inicio) * 1000)
    req_id = getattr(request, 'gateway_request_id', uuid.uuid4())
    llave = getattr(request, 'api_key', None)
    usuario = getattr(request, 'api_user', None)
    if usuario is None:
        u = getattr(request, 'user', None)
        if u is not None and getattr(u, 'is_authenticated', False):
            usuario = u
    try:
        RegistroGateway.objects.create(
            request_id=req_id,
            metodo=request.method[:10],
            ruta=request.path[:255],
            codigo_estado=status,
            duracion_ms=max(duracion, 0),
            api_key=llave,
            usuario=usuario,
            huella_cliente=huella(request, 'api'),
            bloqueado=bloqueado,
            motivo_bloqueo=motivo[:60],
        )
    except Exception:  # pragma: no cover
        pass
    if bloqueado:
        evento('api_gateway_bloqueado', request, usuario=usuario, motivo=motivo, status=status)


def _respuesta_error(request, inicio, status, codigo, mensaje, motivo=None):
    """Construye una respuesta JSON de bloqueo WAF/Auth con cabeceras de seguridad y registro en bitácora."""
    resp = JsonResponse(
        {
            'ok': False,
            'error': {'codigo': codigo, 'mensaje': mensaje},
            'request_id': str(getattr(request, 'gateway_request_id', '')),
        },
        status=status,
    )
    resp['X-Request-ID'] = str(getattr(request, 'gateway_request_id', ''))
    resp['X-Gateway'] = 'EcoParce-API-Gateway/1.0'
    resp['Cache-Control'] = 'no-store'
    resp['X-Content-Type-Options'] = 'nosniff'
    _registrar_gateway(request, status, inicio, bloqueado=True, motivo=motivo or codigo)
    return resp


def _limitar_api_key(llave):
    """Aplica rate limiting por minuto individualizado para cada API Key en caché."""
    clave_cache = f'rl:apikey:{llave.pk}:{int(time.time() // 60)}'
    if cache.add(clave_cache, 1, 65):
        return True
    try:
        n = cache.incr(clave_cache)
    except ValueError:
        cache.set(clave_cache, 1, 65)
        return True
    return n <= llave.limite_por_minuto


class ApiGatewayMiddleware:
    """Middleware de entrada para /api/v1/:
    - Asigna X-Request-ID.
    - Valida API Key si el cliente envía X-API-Key / Bearer (habilitando POST sin cookie CSRF).
    - Aplica filtros de ruta/query y límite de tamaño de payload.
    - Registra toda petición en RegistroGateway.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/api/v1/'):
            return self.get_response(request)

        inicio = time.monotonic()
        request.gateway_request_id = uuid.uuid4()
        request.api_key = None
        request.api_user = None
        request.gateway_json = None

        # 1. Validar tamaño del payload
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                if int(content_length) > MAX_PAYLOAD_BYTES:
                    return _respuesta_error(
                        request, inicio, 413, 'PAYLOAD_TOO_LARGE',
                        'El cuerpo de la petición supera el máximo permitido (64 KB).',
                    )
            except ValueError:
                return _respuesta_error(request, inicio, 400, 'BAD_CONTENT_LENGTH', 'Cabecera Content-Length inválida.')

        # 2. Filtros de seguridad en ruta y parámetros GET
        amenaza = inspeccionar_texto(request.get_full_path())
        if not amenaza:
            for k, v in request.GET.items():
                amenaza = inspeccionar_texto(k) or inspeccionar_texto(v)
                if amenaza:
                    break
        if amenaza:
            return _respuesta_error(
                request, inicio, 400, amenaza,
                'Petición bloqueada por el filtro de seguridad del API Gateway.',
            )

        # 3. Autenticación por API Key o OAuth 2.0 Bearer JWT (si se envió cabecera)
        clave_plana = extraer_api_key(request)
        if clave_plana:
            llave = ApiKey.validar(clave_plana)
            if llave is not None:
                if not _limitar_api_key(llave):
                    return _respuesta_error(
                        request, inicio, 429, 'RATE_LIMIT',
                        'Límite de peticiones por minuto excedido para esta API Key.',
                    )
                request.api_key = llave
                request.api_user = llave.propietario
                request._dont_enforce_csrf_checks = True
                aplicar_contexto_db(user_id=llave.propietario.pk, role=llave.propietario.rol, bypass=False)
            else:
                usuario_jwt, claims = validar_token_oauth2(clave_plana)
                if usuario_jwt is None:
                    return _respuesta_error(
                        request, inicio, 401, 'INVALID_API_KEY',
                        'Credencial inválida, expirada, revocada o cuenta inactiva.',
                    )
                if not limitar(request, f'oauth2:{usuario_jwt.pk}', maximo=120, segundos=60):
                    return _respuesta_error(
                        request, inicio, 429, 'RATE_LIMIT',
                        'Límite de peticiones por minuto excedido para este token OAuth 2.0.',
                    )
                request.api_user = usuario_jwt
                request.oauth_claims = claims
                request._dont_enforce_csrf_checks = True
                aplicar_contexto_db(user_id=usuario_jwt.pk, role=usuario_jwt.rol, bypass=False)
        else:
            # Rate limit público para clientes sin API Key
            if not limitar(request, 'api_publica', maximo=60, segundos=60):
                return _respuesta_error(
                    request, inicio, 429, 'RATE_LIMIT',
                    'Demasiadas peticiones. Intenta de nuevo en un minuto.',
                )
            # Sin cookie de sesión no hay autenticación ambiental de navegador (evita 403 HTML en clientes API)
            if not request.COOKIES.get(settings.SESSION_COOKIE_NAME):
                request._dont_enforce_csrf_checks = True

        # 4. Validar JSON y filtros en cuerpo POST
        if request.method == 'POST':
            raw = request.body or b''
            if len(raw) > MAX_PAYLOAD_BYTES:
                return _respuesta_error(
                    request, inicio, 413, 'PAYLOAD_TOO_LARGE',
                    'El cuerpo de la petición supera el máximo permitido (64 KB).',
                )
            if raw:
                ctype = (request.META.get('CONTENT_TYPE') or '').lower()
                if 'application/json' not in ctype:
                    return _respuesta_error(
                        request, inicio, 415, 'UNSUPPORTED_MEDIA_TYPE',
                        'Las peticiones POST al API Gateway requieren Content-Type: application/json.',
                    )
                try:
                    cuerpo = json.loads(raw.decode('utf-8'))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return _respuesta_error(request, inicio, 400, 'INVALID_JSON', 'El cuerpo JSON no es válido.')
                if not isinstance(cuerpo, dict):
                    return _respuesta_error(request, inicio, 400, 'INVALID_JSON', 'Se esperaba un objeto JSON.')
                amenaza_body = _inspeccionar_estructura(cuerpo)
                if amenaza_body:
                    return _respuesta_error(
                        request, inicio, 400, amenaza_body,
                        'Contenido bloqueado por el filtro de seguridad del API Gateway.',
                    )
                request.gateway_json = cuerpo
            else:
                request.gateway_json = {}

        respuesta = self.get_response(request)
        respuesta['X-Request-ID'] = str(request.gateway_request_id)
        respuesta['X-Gateway'] = 'EcoParce-API-Gateway/1.0'
        respuesta['Cache-Control'] = 'no-store'
        respuesta['Pragma'] = 'no-cache'
        respuesta['X-Content-Type-Options'] = 'nosniff'
        _registrar_gateway(
            request,
            respuesta.status_code,
            inicio,
            bloqueado=respuesta.status_code in (401, 403, 429),
            motivo=f'HTTP_{respuesta.status_code}' if respuesta.status_code >= 400 else '',
        )
        return respuesta


def endpoint_gateway(metodos=('GET',), requiere_auth=False, requiere_escritura=False, solo_sistema=False):
    """Decorador para vistas del API Gateway: controla métodos, permisos y respuesta JSON estándar."""

    def decorador(vista):
        @wraps(vista)
        def envuelta(request, *args, **kwargs):
            if request.method not in metodos:
                resp = JsonResponse(
                    {
                        'ok': False,
                        'error': {'codigo': 'METHOD_NOT_ALLOWED', 'mensaje': f'Método {request.method} no permitido.'},
                        'request_id': str(getattr(request, 'gateway_request_id', '')),
                    },
                    status=405,
                )
                resp['Allow'] = ', '.join(metodos)
                return resp

            llave = getattr(request, 'api_key', None)
            usuario = getattr(request, 'api_user', None)
            if usuario is None and getattr(request.user, 'is_authenticated', False):
                usuario = request.user

            if (requiere_auth or solo_sistema) and usuario is None:
                return JsonResponse(
                    {
                        'ok': False,
                        'error': {'codigo': 'UNAUTHORIZED', 'mensaje': 'Autenticación requerida (X-API-Key o sesión).'},
                        'request_id': str(getattr(request, 'gateway_request_id', '')),
                    },
                    status=401,
                )

            if requiere_escritura:
                if llave is not None and not llave.permite_escritura():
                    return JsonResponse(
                        {
                            'ok': False,
                            'error': {'codigo': 'FORBIDDEN', 'mensaje': 'Esta API Key es de solo lectura.'},
                            'request_id': str(getattr(request, 'gateway_request_id', '')),
                        },
                        status=403,
                    )
                oauth_claims = getattr(request, 'oauth_claims', None)
                if oauth_claims is not None:
                    scopes = set(str(oauth_claims.get('scope', '')).split())
                    if 'write' not in scopes:
                        return JsonResponse(
                            {
                                'ok': False,
                                'error': {'codigo': 'INSUFFICIENT_SCOPE', 'mensaje': 'El token OAuth 2.0 no tiene permiso write.'},
                                'request_id': str(getattr(request, 'gateway_request_id', '')),
                            },
                            status=403,
                        )

            if solo_sistema and not (usuario and usuario.es_admin_sistema()):
                return JsonResponse(
                    {
                        'ok': False,
                        'error': {'codigo': 'FORBIDDEN', 'mensaje': 'Requiere rol de administrador del sistema.'},
                        'request_id': str(getattr(request, 'gateway_request_id', '')),
                    },
                    status=403,
                )

            request.api_actor = usuario
            return vista(request, *args, **kwargs)

        return envuelta

    return decorador
