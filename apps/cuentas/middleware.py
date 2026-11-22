"""Control de acceso centralizado (OWASP A01 y A07).

1. Toda persona con sesión debe haber aceptado la versión vigente del aviso de privacidad (Ley 1581).
2. El panel (/panel/) solo admite administradores activos que:
   - tengan la verificación en dos pasos (TOTP) configurada, y
   - hayan completado esa verificación en la sesión actual;
   - si PANEL_SOLO_GOOGLE está activo, hayan entrado con Google.
3. La sesión del panel se cierra tras 30 minutos sin actividad.
"""
import time

from allauth.account.authentication import get_authentication_records
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from apps.core.seguridad import evento

LIBRES = ('/static/', '/media/', '/accounts/', '/cuenta/autorizacion/', '/privacidad/', '/terminos/', '/.well-known/')


class ControlAccesoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, 'user', None)
        if usuario is not None and usuario.is_authenticated:
            respuesta = self._revisar(request, usuario)
            if respuesta is not None:
                return respuesta
        return self.get_response(request)

    def _revisar(self, request, usuario):
        ruta = request.path
        if ruta.startswith(LIBRES):
            return None

        if request.session.get('consentimiento') != settings.VERSION_AVISO_PRIVACIDAD:
            if usuario.consentimiento_vigente():
                request.session['consentimiento'] = settings.VERSION_AVISO_PRIVACIDAD
            else:
                return redirect(f"{reverse('cuentas:autorizacion')}?next={request.get_full_path()}")

        if not ruta.startswith('/panel/'):
            return None

        if not usuario.es_personal:
            evento('panel_acceso_denegado', request)
            raise PermissionDenied('El panel es solo para administradores.')

        registros = get_authentication_records(request, usuario)
        metodos = {r.get('method') for r in registros}

        if settings.PANEL_SOLO_GOOGLE and 'socialaccount' not in metodos:
            return self._expulsar(request, 'Por seguridad, el panel exige iniciar sesión con Google.')

        if settings.EXIGIR_MFA_PANEL:
            if not usuario.tiene_mfa():
                messages.warning(request, 'Antes de usar el panel, activa la verificación en dos pasos.')
                return redirect('mfa_activate_totp')
            if 'mfa' not in metodos:
                return self._expulsar(request, 'Tu sesión no completó la verificación en dos pasos. Ingresa de nuevo.')

        ahora = int(time.time())
        ultima = request.session.get('panel_ultima_actividad')
        if ultima and ahora - ultima > settings.PANEL_INACTIVIDAD_SEGUNDOS:
            return self._expulsar(request, 'La sesión del panel se cerró por inactividad.')
        request.session['panel_ultima_actividad'] = ahora
        return None

    def _expulsar(self, request, mensaje):
        evento('panel_sesion_cerrada', request, motivo=mensaje)
        logout(request)
        messages.warning(request, mensaje)
        return redirect(f"{reverse('account_login')}?next=/panel/")
