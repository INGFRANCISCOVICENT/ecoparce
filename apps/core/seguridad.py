"""Utilidades de seguridad: IP del cliente y límites de frecuencia sin guardar datos personales.

La IP nunca se escribe en la base de datos (RN-08): solo se usa, convertida en un resumen HMAC
que cambia cada hora, como llave temporal en la caché para frenar abusos."""
import hashlib
import hmac
import logging
import time

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger('ecoparce.seguridad')


def ip_cliente(request):
    cabecera = getattr(settings, 'IP_CABECERA_CONFIABLE', None)
    if cabecera and request.META.get(cabecera):
        return request.META[cabecera].split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def huella(request, contexto=''):
    """Resumen no reversible de la IP + agente de usuario, rotado cada hora."""
    ventana = int(time.time() // 3600)
    dato = f'{ip_cliente(request)}|{request.META.get("HTTP_USER_AGENT", "")[:200]}|{contexto}|{ventana}'
    return hmac.new(settings.SECRET_KEY.encode(), dato.encode(), hashlib.sha256).hexdigest()[:32]


def limitar(request, accion, maximo, segundos):
    """Devuelve True si la acción está permitida; False si superó el límite en la ventana."""
    clave = f'rl:{accion}:{huella(request, accion)}'
    if cache.add(clave, 1, segundos):
        return True
    try:
        n = cache.incr(clave)
    except ValueError:
        cache.set(clave, 1, segundos)
        return True
    if n > maximo:
        if n == maximo + 1:
            log.warning('Límite superado: %s', accion)
        return False
    return True


def evento(tipo, request=None, usuario=None, **datos):
    """Registro estructurado de eventos de seguridad (sin IP de visitantes)."""
    quien = getattr(usuario, 'correo', None) or getattr(getattr(request, 'user', None), 'correo', '-')
    extras = ' '.join(f'{k}={v}' for k, v in datos.items())
    log.info('evento=%s usuario=%s ruta=%s %s', tipo, quien, getattr(request, 'path', '-'), extras)
