from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def panel_requerido(vista):
    """Cualquier administrador activo (de contenido o del sistema). Los visitantes reciben 403."""
    @login_required
    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        if not request.user.es_personal:
            raise PermissionDenied('El panel es solo para administradores.')
        return vista(request, *args, **kwargs)
    return envuelta


def sistema_requerido(vista):
    """RN-09: QR, estadísticas, usuarios y eliminación solo para el administrador del sistema."""
    @login_required
    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        if not request.user.es_admin_sistema():
            raise PermissionDenied('Esta sección es solo para el administrador del sistema.')
        return vista(request, *args, **kwargs)
    return envuelta
