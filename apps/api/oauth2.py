"""Servidor OAuth 2.0 endurecido (RFC 6749, RFC 7519, RFC 7009, RFC 7662, RFC 8725, RFC 9700).

Controles aplicados:
- Firma HS256 con clave derivada dedicada (separada de SECRET_KEY) y validación estricta de cabecera (alg/typ).
- Separación estricta de uso de token (token_use='access' vs 'refresh') para evitar confusión de tokens.
- Rotación de Refresh Tokens de un solo uso con detección de reutilización (revoca toda la familia).
- Revocación inmediata por jti (RFC 7009) e introspección estándar (RFC 7662).
- Validación de scopes (read / write) en el API Gateway.
"""
import hashlib
import time
import uuid

import jwt
from django.conf import settings
from django.core.cache import cache

from apps.cuentas.models import Usuario

OAUTH_ISSUER = 'ecoparce-oauth2'
OAUTH_AUDIENCE = 'ecoparce-api'
OAUTH_ACCESS_TTL = 15 * 60          # 15 minutos
OAUTH_REFRESH_TTL = 7 * 24 * 3600   # 7 días


def _clave_jwt():
    """Deriva la clave de firma HS256 con dominio separado de SECRET_KEY."""
    return hashlib.sha256(('oauth2-jwt-v2|' + settings.SECRET_KEY).encode('utf-8')).hexdigest()


def _emitir_jwt(usuario, scope, token_use, ttl, familia):
    """Genera y firma un JWT (access o refresh) con claims estándar RFC 7519 y familia de rotación."""
    ahora = int(time.time())
    jti = str(uuid.uuid4())
    payload = {
        'iss': OAUTH_ISSUER,
        'aud': OAUTH_AUDIENCE,
        'sub': str(usuario.pk),
        'email': usuario.correo,
        'rol': usuario.rol,
        'scope': scope,
        'token_use': token_use,
        'fam': familia,
        'iat': ahora,
        'nbf': ahora,
        'exp': ahora + ttl,
        'jti': jti,
    }
    return jwt.encode(payload, _clave_jwt(), algorithm='HS256', headers={'typ': 'JWT'}), jti


def emitir_par_tokens_oauth2(usuario, scope='read write', familia=None):
    """Emite access_token + refresh_token rotativo conforme a RFC 6749 y RFC 9700."""
    fam = familia or str(uuid.uuid4())
    access_token, _ = _emitir_jwt(usuario, scope, 'access', OAUTH_ACCESS_TTL, fam)
    refresh_token, refresh_jti = _emitir_jwt(usuario, scope, 'refresh', OAUTH_REFRESH_TTL, fam)
    cache.set(f'oauth2:rt_active:{refresh_jti}', fam, OAUTH_REFRESH_TTL)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': OAUTH_ACCESS_TTL,
        'scope': scope,
    }


def _decodificar_estricto(token, uso_esperado=None):
    """Decodifica un JWT aplicando RFC 8725 (rechaza alg:none, claims faltantes y uso incorrecto)."""
    if not token or not isinstance(token, str) or token.count('.') != 2:
        return None
    try:
        header = jwt.get_unverified_header(token)
        if header.get('alg') != 'HS256' or header.get('typ') != 'JWT':
            return None
        claims = jwt.decode(
            token,
            _clave_jwt(),
            algorithms=['HS256'],
            audience=OAUTH_AUDIENCE,
            issuer=OAUTH_ISSUER,
            options={'require': ['exp', 'iat', 'nbf', 'iss', 'aud', 'sub', 'jti', 'token_use', 'fam']},
        )
    except jwt.PyJWTError:
        return None

    if uso_esperado and claims.get('token_use') != uso_esperado:
        return None
    if cache.get(f"oauth2:revoked:{claims['jti']}") or cache.get(f"oauth2:fam_revoked:{claims['fam']}"):
        return None
    return claims


def rotar_refresh_token(refresh_token):
    """Rota un refresh_token de un solo uso. Si se intenta reutilizar uno ya usado, revoca toda la familia."""
    claims = _decodificar_estricto(refresh_token, uso_esperado='refresh')
    if claims is None:
        return None, None
    jti = claims['jti']
    fam = claims['fam']

    # Detección de reutilización (RFC 9700): si el jti ya fue consumido, comprometieron el token -> revocar familia
    if cache.get(f'oauth2:rt_used:{jti}'):
        cache.set(f'oauth2:fam_revoked:{fam}', True, OAUTH_REFRESH_TTL)
        return None, 'REFRESH_TOKEN_REUSE'

    if not cache.get(f'oauth2:rt_active:{jti}'):
        return None, 'INVALID_REFRESH'

    try:
        usuario = Usuario.objects.get(pk=int(claims['sub']), is_active=True)
    except (Usuario.DoesNotExist, ValueError):
        return None, 'USER_INACTIVE'

    cache.delete(f'oauth2:rt_active:{jti}')
    cache.set(f'oauth2:rt_used:{jti}', True, OAUTH_REFRESH_TTL)
    return emitir_par_tokens_oauth2(usuario, scope=claims.get('scope', 'read'), familia=fam), None


def revocar_token_oauth2(token):
    """Revoca un access o refresh token (RFC 7009). Si es refresh, revoca toda su familia."""
    claims = _decodificar_estricto(token)
    if claims is None:
        return False
    restante = max(int(claims.get('exp', 0) - time.time()), 60)
    cache.set(f"oauth2:revoked:{claims['jti']}", True, restante)
    if claims.get('token_use') == 'refresh':
        cache.delete(f"oauth2:rt_active:{claims['jti']}")
        cache.set(f"oauth2:fam_revoked:{claims['fam']}", True, OAUTH_REFRESH_TTL)
    return True


def validar_token_oauth2(token):
    """Valida estrictamente un access_token Bearer JWT. Rechaza refresh tokens."""
    claims = _decodificar_estricto(token, uso_esperado='access')
    if claims is None:
        return None, None
    try:
        usuario = Usuario.objects.get(pk=int(claims['sub']), is_active=True)
    except (Usuario.DoesNotExist, ValueError):
        return None, None
    return usuario, claims


def introspeccionar_token_oauth2(token):
    """RFC 7662: devuelve {'active': True, ...} si el token es válido y vigente, o {'active': False}."""
    claims = _decodificar_estricto(token)
    if claims is None:
        return {'active': False}
    if claims.get('token_use') == 'refresh' and cache.get(f"oauth2:rt_used:{claims['jti']}"):
        return {'active': False}
    try:
        usuario = Usuario.objects.get(pk=int(claims['sub']), is_active=True)
    except (Usuario.DoesNotExist, ValueError):
        return {'active': False}
    return {
        'active': True,
        'sub': str(usuario.pk),
        'username': usuario.correo,
        'scope': claims.get('scope', ''),
        'token_type': 'Bearer',
        'token_use': claims.get('token_use'),
        'exp': claims.get('exp'),
        'iat': claims.get('iat'),
        'iss': claims.get('iss'),
        'aud': claims.get('aud'),
        'jti': claims.get('jti'),
    }
